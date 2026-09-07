# -*- coding: utf-8 -*-
"""Interoperability tests for canonical Ed25519 did:key encoding.

The fixed vector below comes from the W3C CCG did:key Method test vectors.
The independent decoder intentionally does not use PCM's production base58
helpers, so it catches accidental changes to the wire encoding.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.pcm.identity import did_from_pubkey, pubkey_from_did


W3C_ED25519_PUBLIC_KEY = bytes.fromhex(
    "095f9a1a595dde755d82786864ad03dfa5a4fbd68832566364e2b65e13cc9e44"
)
W3C_ED25519_DID = (
    "did:key:z6Mkf5rGMoatrSj1f4CyvuHBeXJELe9RPdzo2PKGNCKVtZxP"
)
ED25519_MULTICODEC = b"\xed\x01"
BASE58BTC_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _independent_base58btc_decode(text: str) -> bytes:
    """Minimal test-only base58btc decoder independent of production code."""
    value = 0
    for char in text:
        try:
            digit = BASE58BTC_ALPHABET.index(char)
        except ValueError as exc:
            raise ValueError(f"invalid base58btc character: {char!r}") from exc
        value = value * 58 + digit

    decoded = value.to_bytes((value.bit_length() + 7) // 8, "big") if value else b""
    leading_zeroes = len(text) - len(text.lstrip("1"))
    return (b"\x00" * leading_zeroes) + decoded


def test_w3c_ed25519_vector_encodes_canonically():
    assert did_from_pubkey(W3C_ED25519_PUBLIC_KEY) == W3C_ED25519_DID


def test_w3c_ed25519_vector_decodes_canonically():
    assert pubkey_from_did(W3C_ED25519_DID) == W3C_ED25519_PUBLIC_KEY


def test_w3c_vector_round_trips():
    did = did_from_pubkey(W3C_ED25519_PUBLIC_KEY)
    assert pubkey_from_did(did) == W3C_ED25519_PUBLIC_KEY


def test_generated_wire_format_is_independently_decodable():
    did = did_from_pubkey(W3C_ED25519_PUBLIC_KEY)
    assert did.startswith("did:key:z")

    payload = _independent_base58btc_decode(did.removeprefix("did:key:z"))
    assert payload[:2] == ED25519_MULTICODEC
    assert payload[2:] == W3C_ED25519_PUBLIC_KEY


def test_base64url_disguised_as_z_multibase_is_rejected():
    # Regression for issue #17: '-' and '_' are not base58btc characters.
    malformed = "did:key:z7Q_6-a-base64url-value"
    try:
        pubkey_from_did(malformed)
    except (ValueError, TypeError):
        pass
    else:
        raise AssertionError("non-base58btc did:key:z value was accepted")
