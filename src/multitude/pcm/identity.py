# -*- coding: utf-8 -*-
"""PCM node identity — did:key generation and storage (Phase 0).

Implements docs/NETWORKING_STACK.md §4.2 Move 1: every PCM node (human,
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

The file contains the DID, the raw secret seed (32 bytes, base64), and a
created timestamp. It is sensitive long-term signing-key material. On POSIX,
PCM creates the identity directory as ``0700`` and the key file as ``0600``.
Losing this file means losing the node's identity; leaking it means another
process can impersonate the node. Back it up only to storage with equivalent
access controls. See ``docs/IDENTITY_SECURITY.md``.

Dependencies: cryptography and base58 are required PCM dependencies.
Canonical base58btc encoding is mandatory because a ``did:key:z...`` value
uses the multibase ``z`` prefix and therefore MUST contain base58btc data.
"""
from __future__ import annotations

import base64
import json
import os
import stat
import tempfile
import warnings
import stat
import tempfile
import warnings
from datetime import datetime, timezone
from pathlib import Path

import base58
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_ED25519_MULTICODEC = b"\xed\x01"
_MULTIBASE_B58 = "z"
_PRIVATE_DIRECTORY_MODE = 0o700
_PRIVATE_FILE_MODE = 0o600


def _b58(data: bytes) -> str:
    """Encode bytes as canonical base58btc for multibase ``z`` values."""
    return base58.b58encode(data).decode("ascii")


def _b58d(text: str) -> bytes:
    """Decode canonical base58btc used by multibase ``z`` values."""
    return base58.b58decode(text)


def did_from_pubkey(pubkey: bytes) -> str:
    """Raw Ed25519 public key -> canonical base58btc did:key string."""
    if len(pubkey) != 32:
        raise ValueError("Ed25519 public keys are 32 bytes")
    return "did:key:" + _MULTIBASE_B58 + _b58(_ED25519_MULTICODEC + pubkey)


def pubkey_from_did(did: str) -> bytes:
    """Canonical base58btc Ed25519 did:key string -> raw public key bytes."""
    prefix = "did:key:" + _MULTIBASE_B58
    if not did.startswith(prefix):
        raise ValueError(f"not an ed25519 base58btc did:key: {did!r}")
    body = _b58d(did[len(prefix):])
    if body[:2] != _ED25519_MULTICODEC:
        raise ValueError("did:key body does not start with the ed25519 multicodec")
    pubkey = body[2:]
    if len(pubkey) != 32:
        raise ValueError("ed25519 multicodec body must be 32 bytes")
    return pubkey


def _prepare_identity_directory(directory: Path) -> None:
    """Create the private-key directory and harden it on POSIX."""
    directory.mkdir(parents=True, exist_ok=True, mode=_PRIVATE_DIRECTORY_MODE)
    if os.name == "posix":
        os.chmod(directory, _PRIVATE_DIRECTORY_MODE)


def _write_identity_atomic(path: Path, identity: dict) -> None:
    """Write identity JSON through an owner-only temporary file."""
    fd = -1
    tmp_path: Path | None = None
    try:
        # mkstemp creates the file atomically with mode 0600 on POSIX.  The
        # explicit fchmod happens before any secret key bytes are written.
        fd, tmp_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        tmp_path = Path(tmp_name)
        if os.name == "posix":
            os.fchmod(fd, _PRIVATE_FILE_MODE)

        stream = os.fdopen(fd, "w", encoding="utf-8", newline="\n")
        fd = -1  # ownership transferred to stream
        with stream:
            json.dump(identity, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(tmp_path, path)
    except Exception:
        if fd >= 0:
            os.close(fd)
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
        raise


def _check_identity_permissions(path: Path, *, strict: bool) -> None:
    """Warn, or fail closed, when a POSIX private-key file is too broad."""
    if os.name != "posix":
        return

    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & (stat.S_IRWXG | stat.S_IRWXO) == 0:
        return

    message = (
        f"PCM identity file {path} has mode {mode:04o}; expected 0600 because "
        "it contains the node's private signing key. Run chmod 600 on it."
    )
    if strict:
        raise PermissionError(message)
    warnings.warn(message, RuntimeWarning, stacklevel=2)


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
    _prepare_identity_directory(d)
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
    _write_identity_atomic(path, identity)
    return identity


def load_identity(node_dir: str | os.PathLike, *,
                  strict_permissions: bool = False) -> dict:
    """Load an identity, checking private-key permissions on POSIX.

    Broad group/other permissions emit a warning by default. Pass
    ``strict_permissions=True`` to reject such a file instead.
    """
    path = Path(node_dir) / "identity" / "pcm_identity.json"
    if not path.exists():
        raise FileNotFoundError(
            f"no PCM identity at {path} — run generate_identity() first")
    _check_identity_permissions(path, strict=strict_permissions)
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
