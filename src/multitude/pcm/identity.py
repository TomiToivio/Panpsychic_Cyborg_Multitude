# -*- coding: utf-8 -*-
"""PCM node identity — did:key generation and storage (Phase 0).

Implements NETWORKING_STACK.md §4.2 Move 1: every PCM node (human,
personal agent, device, collective) gets one persistent, vendor-independent
identity as a W3C ``did:key`` over Ed25519.

Format (did:key multicodec, standard):

    did:key:z<base58btc(multibase-varint-prefixed pubkey)>

Ed25519 32-byte public keys use multicodec code 0xed 0x01. The
multibase prefix ``z`` means base58btc. So the did:key body is
base58btc(0xed 0x01 || raw_pubkey) — exactly what the spec's envelope
``from``/``to`` fields carry.

Storage: the private key lives with the user (never in events.jsonl,
never over the network), at:

    <node_dir>/identity/pcm_identity.json

containing the DID, the raw secret seed (32 bytes, base64) and a
created timestamp. Losing this file means losing the node's identity —
back it up. Rotation = new DID + a signed successor credential (Phase 3).

Dependencies: cryptography (already a PCM dependency chain member),
base58 (optional extra; falls back to base64url if absent).
"""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

try:  # optional extra; base58btc is the standard did:key encoding
    import base58 as _base58
except ImportError:  # pragma: no cover - fallback path
    _base58 = None

_ED25519_MULTICODEC = b"\xed\x01"
_MULTIBASE_B58 = "z"


def _b58(data: bytes) -> str:
    if _base58 is not None:
        return _base58.b58encode(data).decode("ascii")
    # fallback: base64url without padding (NOT canonical did:key, but stable)
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b58d(text: str) -> bytes:
    if _base58 is not None:
        return _base58.b58decode(text)
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def did_from_pubkey(pubkey: bytes) -> str:
    """Raw Ed25519 public key -> did:key string."""
    if len(pubkey) != 32:
        raise ValueError("Ed25519 public keys are 32 bytes")
    return "did:key:z" + _b58(_ED25519_MULTICODEC + pubkey)


def pubkey_from_did(did: str) -> bytes:
    """did:key string -> raw Ed25519 public key (32 bytes)."""
    if not did.startswith("did:key:z"):
        raise ValueError(f"not an ed25519 did:key: {did!r}")
    body = _b58d(did[len("did:key:z"):])
    if body[:2] != _ED25519_MULTICODEC:
        raise ValueError("did:key body does not start with the ed25519 multicodec")
    pubkey = body[2:]
    if len(pubkey) != 32:
        raise ValueError("ed25519 multicodec body must be 32 bytes")
    return pubkey


def generate_identity(node_dir: str | os.PathLike,
                      force: bool = False) -> dict:
    """Generate a fresh Ed25519 node identity and store it.

    Idempotent: an existing identity file is returned untouched unless
    force=True (which archives nothing — the old identity is gone; use
    only for resets).
    """
    d = Path(node_dir) / "identity"
    path = d / "pcm_identity.json"
    if path.exists() and not force:
        return load_identity(node_dir)
    d.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    seed = key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    pub = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    identity = {
        "did": did_from_pubkey(pub),
        "public_key_hex": pub.hex(),
        "secret_seed_b64": base64.b64encode(seed).decode(),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "algorithm": "ed25519",
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(identity, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return identity


def load_identity(node_dir: str | os.PathLike) -> dict:
    path = Path(node_dir) / "identity" / "pcm_identity.json"
    if not path.exists():
        raise FileNotFoundError(
            f"no PCM identity at {path} — run generate_identity() first")
    return json.loads(path.read_text(encoding="utf-8"))


def private_key_from_identity(identity: dict) -> Ed25519PrivateKey:
    seed = base64.b64decode(identity["secret_seed_b64"])
    return Ed25519PrivateKey.from_private_bytes(seed)


def public_key_from_identity(identity: dict) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(bytes.fromhex(identity["public_key_hex"]))


def verify_did_binding(identity: dict) -> bool:
    """True when the stored DID actually derives from the stored public key."""
    pub = bytes.fromhex(identity["public_key_hex"])
    return identity["did"] == did_from_pubkey(pub)