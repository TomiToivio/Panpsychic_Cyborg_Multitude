# -*- coding: utf-8 -*-
"""VC capability grants — Phase 3 'trusted' layer (NETWORKING_STACK.md §7).

Closes the roadmap line: Phase 3 — VC capability grants.

The four authorization states (policy.py §7):

    reachable      zenoh addresses a node          (fabric)
    authenticated  signature verifies              (envelope.verify)
    authorized     local policy allows             (pcm.policy)
    trusted        long-term relationships         (THIS module)

A Verifiable Credential here is deliberately minimal: a capability
grant signed by the GRANTOR's did:key, verifiable by anyone holding
the grantor's did — no issuer registry, no blockchain, no trusted
third party. It is the portable form of an explicit policy rule: the
holder can PRESENT it to any node, and the node can VERIFY it offline
before extending policy to a stranger.

What a grant says:

    "The rhizome (or node) with did <issuer> grants the node with did
     <subject> capability <action> on <target> from <not_before> until
     <expires>, under constraints <limits>."

Design:

- **did:key signatures only.** Ed25519 over the same canonicalization
  as pcm/envelope.py — one crypto path, one trust root.
- **No PKI.** Verification = the issuer's did resolves to the pubkey
  that signed. Trust in the ISSUER is a local policy question; the VC
  itself is tamper-evident evidence, not authority.
- **Revocation by expiry-first.** Short-lived grants beat revocation
  lists in a local-first network; a `revoked` flag rides the local
  store and is checked at verify time. Revocation propagates as new
  events, never silent overwrites.
- **Policy integration is explicit.** A grant never auto-grants. The
  node's Policy acquires a rule FROM the grant only when the operator
  (or an explicit boot rule) calls `Policy.admit_vc`. Fail-closed
  survives: without admission, a valid VC is just paper.

Envelope ride-along: grants travel in `capability_grant` envelopes
(closed vocabulary, Phase 0) — presented envelopes are verified by the
same edge verification as every other message.

Public surface:

    CapabilityGrant       — the VC dataclass (issue/sign/verify/parse)
    GrantDenied           — verification or validity failure
    VcPolicyBridge        — wire verified grants into a local Policy
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from multitude.pcm.envelope import canonical_bytes
from multitude.pcm.identity import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
    did_from_pubkey,
    pubkey_from_did,
)

VC_SCHEMA = "pcm.vc.capability/1"


class GrantDenied(ValueError):
    """A capability grant failed verification or is not currently valid."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class CapabilityGrant:
    """One signed capability grant (minimal Verifiable Credential).

    sig covers the canonical JSON of every field except ``sig`` —
    same rule as the PCM envelope, so verification code is shared.
    """

    issuer: str                     # did:key of the grantor
    subject: str                    # did:key of the grantee
    action: str                     # fnmatch pattern, e.g. "light.*"
    target: str = "*"               # fnmatch pattern over pcm id
    granted_at: str = ""
    not_before: str = ""            # empty = immediately
    expires: str = ""               # empty = no expiry (discouraged)
    max_per_minute: int | None = None
    parameter_limits: dict[str, tuple[float, float]] = field(default_factory=dict)
    note: str = ""
    revoked: bool = False
    sig: str = ""

    # -- construction -------------------------------------------------------

    @classmethod
    def issue(cls, issuer_did: str, subject_did: str, action: str,
              target: str = "*", *, days: float = 30.0,
              max_per_minute: int | None = None,
              parameter_limits: dict[str, tuple[float, float]] | None = None,
              note: str = "") -> "CapabilityGrant":
        now = _now()
        return cls(
            issuer=issuer_did, subject=subject_did, action=action,
            target=target, granted_at=_iso(now), not_before=_iso(now),
            expires=_iso(now + timedelta(days=days)),
            max_per_minute=max_per_minute,
            parameter_limits=dict(parameter_limits or {}), note=note,
        )

    # -- signing / verification -------------------------------------------

    def unsigned_payload(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if k != "sig"}

    def sign(self, private_key: Ed25519PrivateKey, expected_issuer: str) -> str:
        if not self.granted_at:
            self.granted_at = _iso(_now())
        actual = did_from_pubkey(_pub_raw(private_key))
        if actual != self.issuer or expected_issuer != self.issuer:
            raise GrantDenied(
                f"signing key {actual!r} does not match grant issuer {self.issuer!r}")
        digest = canonical_bytes(self.unsigned_payload())
        self.sig = "ed25519:" + private_key.sign(digest).hex()
        return self.sig

    def verify(self) -> None:
        """Full verification: signature, issuer binding, validity window.

        Raises GrantDenied with the reason on any failure.
        """
        if not self.sig.startswith("ed25519:"):
            raise GrantDenied("missing or malformed signature")
        if self.revoked:
            raise GrantDenied("grant is revoked")
        try:
            pubkey = pubkey_from_did(self.issuer)
        except ValueError as e:
            raise GrantDenied(f"bad issuer did: {e}") from e
        digest = canonical_bytes(self.unsigned_payload())
        sig_bytes = bytes.fromhex(self.sig[len("ed25519:"):])
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey as _Key,
        )
        key_obj = _Key.from_public_bytes(pubkey)
        try:
            key_obj.verify(sig_bytes, digest)
        except InvalidSignature:
            raise GrantDenied("signature does not verify against issuer did")
        # validity window (all comparisons in UTC; empty = open bound)
        now = _now()
        if self.not_before:
            if now < datetime.strptime(self.not_before, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc):
                raise GrantDenied("grant not yet active (not_before in the future)")
        if self.expires:
            if now > datetime.strptime(self.expires, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc):
                raise GrantDenied("grant expired")

    # -- serialization -----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityGrant":
        limits = data.get("parameter_limits") or {}
        fixed = {k: tuple(v) for k, v in limits.items() if isinstance(v, list)}
        return cls(
            issuer=data.get("issuer", ""), subject=data.get("subject", ""),
            action=data.get("action", ""), target=data.get("target", "*"),
            granted_at=data.get("granted_at", ""), not_before=data.get("not_before", ""),
            expires=data.get("expires", ""),
            max_per_minute=data.get("max_per_minute"),
            parameter_limits=fixed, note=data.get("note", ""),
            revoked=bool(data.get("revoked", False)), sig=data.get("sig", ""),
        )

    # -- envelope ----------------------------------------------------------

    def to_envelope(self, private_key: Ed25519PrivateKey) -> dict[str, Any]:
        """Wrap into a signed capability_grant envelope for the fabric."""
        from multitude.pcm.envelope import Envelope
        env = Envelope.create(
            "capability_grant", self.issuer, self.subject,
            {"grant": self.to_dict()}, interface="pcm.transport",
        )
        env.sign(private_key, self.issuer)
        return env.model_dump(by_alias=True)

    @classmethod
    def from_envelope(cls, envelope_dict: dict[str, Any]) -> "CapabilityGrant":
        """Parse a grant from a verified capability_grant envelope.

        Both signatures are checked: the ENVELOPE (transport-level,
        authorship) and the GRANT (credential-level, authorization).
        """
        from multitude.pcm.envelope import Envelope
        env = Envelope.model_validate(envelope_dict)
        env.verify()
        if env.type != "capability_grant":
            raise GrantDenied(f"envelope type {env.type!r} is not capability_grant")
        grant = cls.from_dict((env.content or {}).get("grant") or {})
        if grant.issuer != env.from_did:
            raise GrantDenied("grant issuer does not match envelope author")
        grant.verify()          # credential-level signature + validity
        return grant


class VcPolicyBridge:
    """Wire VERIFIED grants into a local Policy as explicit rules.

    The bridge never weakens fail-closed: admitting a grant appends one
    explicit PolicyRule scoped to the grant's action/target/subject,
    with the grant's own limits carried over. High-risk actions still
    demand the explicit-rule match this rule provides — a wildcard
    grant to a high-risk action pattern is admitted but its rule keeps
    the explicit scope, so the high-risk gate stays satisfied honestly.
    """

    def __init__(self) -> None:
        self.grants: dict[str, CapabilityGrant] = {}  # key: sig hash prefix

    def admit(self, grant: CapabilityGrant) -> str:
        """Verify then register. Returns the registration key."""
        grant.verify()
        key = grant.sig[:24]
        self.grants[key] = grant
        return key

    def revoke(self, key: str) -> None:
        grant = self.grants.get(key)
        if grant is not None:
            grant.revoked = True

    def rules(self) -> list:
        """PolicyRule list derived from currently-valid grants."""
        from multitude.pcm.policy import PolicyRule
        out = []
        for grant in self.grants.values():
            try:
                grant.verify()
            except GrantDenied:
                continue  # expired or revoked: rule disappears
            out.append(PolicyRule(
                action=grant.action, target=grant.target,
                allowed_authors=(grant.subject,),
                max_per_minute=grant.max_per_minute,
                parameter_limits=dict(grant.parameter_limits),
                note=f"vc:{grant.sig[:24]} from {grant.issuer[:20]}…",
            ))
        return out


def _pub_raw(private_key: Ed25519PrivateKey) -> bytes:
    from cryptography.hazmat.primitives import serialization
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


__all__ = [
    "VC_SCHEMA",
    "CapabilityGrant",
    "GrantDenied",
    "VcPolicyBridge",
]