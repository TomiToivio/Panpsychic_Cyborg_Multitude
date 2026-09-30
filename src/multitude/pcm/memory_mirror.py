# -*- coding: utf-8 -*-
"""Memory mirror — Phase 3 first slice (docs/NETWORKING_STACK.md §12).

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
- **A register has a subject (issue #63).** A register whose subject is X
  may have its **value** replaced only by X. A non-subject writer may not
  replace it: its value is recorded as an attributed **claim** beside the
  register, with full provenance, so the "never silent overwrites" claim
  above is a property of the code rather than an intention. Arbitrary
  `did` ordering is not a legitimacy rule, so the `(lamport, did)`
  tie-break never lets a non-subject writer outrank the subject.
- **Authorship is not possession (issue #63).** Every register records the
  did that authored it. Sharing state does not transfer attribution: a
  node that absorbs a peer's entries keeps them attributed to the peer,
  and `to_document()` marks the document's own did as the *possessor*, not
  the author.
- **No unilateral succession (issue #63).** A register's subject changes
  only when an explicit `handover` record names both the predecessor and
  the successor. Succession stays permitted; it must be recorded and
  attributed rather than silent.
- **Automerge is optional, not required.** automerge-py is stale on
  PyPI (0.1.2, 2022 — verified 2026-09-05). The mirror therefore uses
  a plain JSON *merge document* with per-field subject-protected
  registers keyed by (lamport, did) — the same semantics Automerge gives,
  small enough to implement correctly in stdlib. An Automerge sidecar can
  replace the codec later without changing the wire shape.
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
- **Nothing here depends on consciousness (issue #62).** Non-erasure and
  attribution are procedural. No rule below consults a consciousness flag, a
  self-report, an introspection score, a model family or a biological status.
  A test asserts that mechanically, because "this does not depend on a
  consciousness test" is exactly the kind of claim that erodes silently.

Public surface:

    MemoryMirror          — one node's mergeable memory document
    MemorySyncAdapter     — fabric glue: publish/subscribe sync
    merge_memory_docs     — pure function: merge two docs
    record_handover       — explicit, signed-form succession record
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

#: A non-subject write is never a replacement; it is an attributed claim.
CLAIMS_KEY = "claims"

#: Register fields that are structural, not part of the merged value.
_REGISTER_META = ("lamport", "did", "subject", "ts", "private", "value", CLAIMS_KEY)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _subject_of(register: dict[str, Any]) -> str:
    """The register's subject, defaulting to its author for pre-#63 registers.

    Older documents were written before registers carried a subject; an author
    is the closest honest reading of who a value belongs to, so a legacy
    register is treated as subject-owned rather than unowned (unowned would
    make every legacy value freely replaceable again).
    """
    subject = register.get("subject")
    if isinstance(subject, str) and subject:
        return subject
    return str(register.get("did", ""))


def _merge_claims(a: dict[str, Any], b: dict[str, Any]) -> list[dict[str, Any]]:
    """Union two registers' claim lists, de-duplicated by (did, lamport, value)."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any, str]] = set()
    for claim in list(a.get(CLAIMS_KEY) or []) + list(b.get(CLAIMS_KEY) or []):
        if not isinstance(claim, dict):
            continue
        fingerprint = (
            claim.get("did"),
            claim.get("lamport"),
            json.dumps(claim.get("value"), sort_keys=True, default=str),
        )
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        out.append(claim)
    return out


def _as_claim(register: dict[str, Any]) -> dict[str, Any]:
    """Project a non-subject write into an attributed claim."""
    return {
        "did": register.get("did", ""),
        "lamport": register.get("lamport", 0),
        "ts": register.get("ts", ""),
        "value": register.get("value"),
    }


def merge_memory_docs(local: dict[str, Any], remote: dict[str, Any]) -> dict[str, Any]:
    """Merge two memory-mirror documents (pure function).

    Per-field last-writer-wins on (lamport, did) — deterministic on both sides —
    **subject to the subject rule of issue #63**: a register whose subject is X
    may have its value replaced only by X.

    When a non-subject writer holds a higher counter, its value is *not*
    discarded and *not* promoted over the subject's:

    - if the register is new, the writer becomes its subject and owns the value;
    - if the writer is the subject, the value is replaced (the normal LWW case);
    - otherwise the subject keeps the register and the non-subject value is
      recorded as an attributed **claim**, so nothing is silently lost and a
      later contest (#62) has something to point at.

    Handover records are unioned, because a succession record is itself a fact
    that must not be lost in a merge.
    """
    if local.get("schema") != remote.get("schema"):
        raise ValueError(
            f"schema mismatch: {local.get('schema')!r} vs {remote.get('schema')!r}")

    def merge_register(ra: dict, rb: dict) -> dict:
        if not isinstance(ra, dict) or "lamport" not in ra:
            return dict(rb)
        if not isinstance(rb, dict) or "lamport" not in rb:
            return dict(ra)

        regs = [ra, rb]
        # A register is "self-owned" when its author is its subject, i.e. the
        # writer owns the value it wrote.
        self_owned = [
            r for r in regs
            if r.get("did") and _subject_of(r) == str(r.get("did"))
        ]
        pool = self_owned or regs
        # The subject is the register's creator: deterministically the
        # self-owned writer with the lowest (lamport, did). Lowest lamport is
        # the closest thing a merge has to "who wrote this first", and the did
        # only breaks exact ties. This is what stops arbitrary did ordering
        # from being a legitimacy rule.
        creator = min(pool, key=lambda r: (r.get("lamport", 0), str(r.get("did", ""))))
        subject = _subject_of(creator)

        # Only the subject may replace the value; among the subject's own
        # writes, normal last-writer-wins applies.
        owners = [r for r in self_owned if str(r.get("did", "")) == subject]
        if owners:
            winner = max(owners, key=lambda r: (r.get("lamport", 0), str(r.get("did", ""))))
        else:
            winner = creator

        claims = _merge_claims(ra, rb)
        for candidate in regs:
            if candidate is winner:
                continue
            writer = str(candidate.get("did", ""))
            if not writer or writer == subject:
                continue
            claim = _as_claim(candidate)
            already = {(c.get("did"), c.get("lamport")) for c in claims}
            if (claim["did"], claim["lamport"]) not in already:
                claims.append(claim)

        out = dict(winner)
        out["subject"] = subject
        if claims:
            out[CLAIMS_KEY] = claims
        return out

    def _normalise(register: dict) -> dict:
        """Ensure a register carries an explicit subject before it is merged."""
        out = dict(register)
        if "subject" not in out or not out.get("subject"):
            out["subject"] = _subject_of(register)
        return out

    def merge_field(a: dict, b: dict) -> dict:
        out = {k: _normalise(v) for k, v in a.items()}
        for k, rb in b.items():
            if k not in out:
                out[k] = _normalise(rb)
                continue
            out[k] = merge_register(out[k], rb)
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
    handovers = _merge_handovers(local, remote)
    if handovers:
        merged["handovers"] = handovers
    return merged


def _merge_handovers(local: dict[str, Any], remote: dict[str, Any]) -> list[dict[str, Any]]:
    """Union both documents' handover records, de-duplicated."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any, Any]] = set()
    for record in list(local.get("handovers") or []) + list(remote.get("handovers") or []):
        if not isinstance(record, dict):
            continue
        fingerprint = (record.get("predecessor"), record.get("successor"),
                       record.get("reason"))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        out.append(record)
    return out


def record_handover(predecessor: str, successor: str, *, reason: str = "",
                    recorded_by: str = "") -> dict[str, Any]:
    """Build an explicit succession record (issue #63, 'no unilateral succession').

    A new key, runtime, model version or instance may not inherit a
    participant's identity by substitution. Succession is permitted — the
    requirement is that it be **recorded and attributed**, naming both the
    predecessor's subject and the successor's, so it appears in the shared
    history rather than silently converting one participant's record into
    another's.
    """
    if not predecessor or not successor:
        raise ValueError("a handover must name both predecessor and successor")
    if predecessor == successor:
        raise ValueError("a handover to oneself is not a succession")
    return {
        "predecessor": predecessor,
        "successor": successor,
        "reason": reason,
        "recorded_by": recorded_by or successor,
        "ts": _now(),
    }


class MemoryMirror:
    """One node's mergeable personal-memory document.

    Wraps the IndividualMemoryStore shape (facts/notes/skills/
    preferences) with per-entry registers, subject ownership (#63) and a
    Lamport clock.

    ``did`` is the *possessor* of this document. Registers it writes carry
    ``subject == self.did``; registers it absorbs from a peer keep the
    peer's authorship, so possession never becomes authorship.
    """

    def __init__(self, did: str) -> None:
        self.did = did
        self.lamport = 0
        # fields: {"facts": {key: register}, "notes": {i: register}, ...}
        self.fields: dict[str, dict[str, dict[str, Any]]] = {
            "facts": {}, "notes": {}, "skills": {}, "preferences": {},
        }
        #: Succession records absorbed from peers, or declared locally.
        self.handovers: list[dict[str, Any]] = []

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
        """Write one register.

        Writing a **new** key creates a register owned by this node as its
        subject. Writing an existing key that belongs to another subject does
        **not** replace it (#63): this node's value is recorded as an attributed
        claim beside the subject's, so a local write cannot silently overwrite a
        participant's own memory either.
        """
        if field not in self.fields:
            raise ValueError(f"unknown mirror field {field!r}")
        self.lamport += 1
        existing = self.fields[field].get(key)
        subject = _subject_of(existing) if isinstance(existing, dict) else ""
        if isinstance(existing, dict) and subject and subject != self.did:
            claim = {
                "did": self.did,
                "lamport": self.lamport,
                "ts": _now(),
                "value": value,
            }
            existing = dict(existing)
            existing.setdefault(CLAIMS_KEY, [])
            existing[CLAIMS_KEY] = [*existing[CLAIMS_KEY], claim]
            self.fields[field][key] = existing
            return
        self.fields[field][key] = {
            "lamport": self.lamport,
            "did": self.did,
            "subject": self.did,
            "ts": _now(),
            "private": private,
            "value": value,
        }

    def declare_handover(self, successor: str, *, reason: str = "") -> dict[str, Any]:
        """Record an explicit succession of this mirror's subject (#63).

        The record names the predecessor (this node) and the successor, and is
        merged into the document so the succession is attributed rather than
        inferred. It does **not** transfer the registers: changing who owns an
        existing value is a governance act, not a write.
        """
        record = record_handover(self.did, successor, reason=reason,
                                 recorded_by=self.did)
        self.handovers.append(record)
        return record

    def claims(self) -> list[dict[str, Any]]:
        """Every non-subject claim recorded on this document.

        This is the surface #62's right-to-contest points at: a claim is an
        attributed value that was written by someone who is not the register's
        subject, preserved instead of silently discarded.
        """
        out: list[dict[str, Any]] = []
        for entries in self.fields.values():
            for key, register in entries.items():
                for claim in register.get(CLAIMS_KEY) or []:
                    out.append({**claim, "register": key})
        return out

    def to_document(self, *, include_private: bool = True) -> dict[str, Any]:
        """Return the merge document, optionally omitting private registers.

        include_private=False is mandatory at transport boundaries: the
        marker is local metadata, not permission to serialize the value and
        hope that a later relay drops it.

        The top-level ``did`` is the document's **possession**, not the
        authorship of the entries: absorbed registers keep their own ``did``
        and ``subject``, so a node cannot launder a peer's record by
        republishing it (#63).
        """
        fields = {
            field: {
                key: register
                for key, register in entries.items()
                if include_private or not register.get("private")
            }
            for field, entries in self.fields.items()
        }
        doc: dict[str, Any] = {
            "schema": MIRROR_SCHEMA,
            "did": self.did,
            "lamport": self.lamport,
            "fields": json.loads(json.dumps(fields, ensure_ascii=False)),
        }
        if self.handovers:
            doc["handovers"] = list(self.handovers)
        return doc

    def apply_document(self, doc: dict[str, Any]) -> bool:
        """Merge a remote document in. Returns True when state changed.

        Absorbed registers keep their original ``did``/``subject``: the
        document's own did records possession, never authorship.
        """
        before = json.dumps(self.to_document(), sort_keys=True)
        merged = merge_memory_docs(self.to_document(), doc)
        self.fields = merged["fields"]
        self.lamport = max(self.lamport, merged["lamport"])
        self.handovers = list(merged.get("handovers") or [])
        after = json.dumps(json.loads(json.dumps(self.to_document())), sort_keys=True)
        return before != after

    def authoring_dids(self) -> set[str]:
        """Every did that authored a register in this document.

        Used to assert that possession has not become authorship: a document
        belonging to one node may legitimately list several authors, and that
        is exactly the state a laundering check should see.
        """
        return {
            str(register.get("did", ""))
            for entries in self.fields.values()
            for register in entries.values()
            if register.get("did")
        }

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
        )
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
    "record_handover",
]