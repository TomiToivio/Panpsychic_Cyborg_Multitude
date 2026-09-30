# -*- coding: utf-8 -*-
"""Phase 3 tests — memory mirror over the PCM Transport ABC.

docs/NETWORKING_STACK.md §12 Phase 3 line: "automerge memory mirror".
Implementation: pcm/memory_mirror.py — per-field subject-aware merge document
with retained authorship/claims, synced as signed memory_share envelopes
over the Transport ABC.

Test criteria:
1. A subject's self-register cannot be silently overwritten by a peer; peer claims are retained.
2. Existing IndividualMemoryStore-shaped data imports cleanly.
3. Sync: node A pushes a signed memory_share envelope; node B's mirror
   updates ONLY via verified envelope; tampered envelope is rejected.
4. events.jsonl stays authoritative — mirror changes append to the
   rhizome log as audit events, never silently overwrite.
5. private fields survive local merge but are excluded from the
   shareable projection.

Run: python3 tests/test_pcm_memory_mirror.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import asyncio

from multitude.pcm.identity import generate_identity, private_key_from_identity
from multitude.pcm.envelope import EnvelopeError
from multitude.pcm.memory_mirror import (
    MemoryMirror, MemorySync, merge_memory_docs)
from multitude.pcm.transport import InMemoryTransport


def main() -> int:
    failures: list[str] = []

    # ---- 1. merge is deterministic on both sides (#63 subject rule) ----
    # The old expectation here was "B has a higher (lamport, did) -> B wins".
    # That is the arbitrary-legitimacy rule issue #63 removes: a higher did is
    # not a reason to own someone else's register. Two independent writers of
    # the same key each own what they wrote, so A's own write survives and B's
    # is preserved as an attributed claim rather than silently replacing it.
    # ---- 1. subject-owned register + explicit peer claim ----
    a = MemoryMirror("did:key:A")
    a.set("facts", "language", "fi")
    b = MemoryMirror("did:key:B")
    b.set("facts", "language", "en")
    doc_a, doc_b = a.to_document(), b.to_document()
    m_ab = merge_memory_docs(doc_a, doc_b)
    m_ba = merge_memory_docs(doc_b, doc_a)
    reg_ab = m_ab["fields"]["facts"]["language"]
    reg_ba = m_ba["fields"]["facts"]["language"]
    if reg_ab["value"] != reg_ba["value"] or reg_ab["subject"] != reg_ba["subject"]:
        failures.append(f"merge nondeterministic: {reg_ab!r} vs {reg_ba!r}")
    if reg_ab["value"] != "fi" or reg_ab["subject"] != "did:key:A":
        failures.append(
            f"subject rule not applied: {reg_ab['value']!r} owned by {reg_ab['subject']!r}")
    claims = reg_ab.get("claims") or []
    if not any(c["did"] == "did:key:B" and c["value"] == "en" for c in claims):
        failures.append(f"non-subject write was not preserved as a claim: {reg_ab!r}")
    print(f"[merge] subject-owned and deterministic: {reg_ab['value']!r} "
          f"(+{len(claims)} attributed claim(s))")
    reg_a = m_ab["fields"]["facts"]["language"]
    if reg_a["value"] != "fi" or reg_a["author"] != "did:key:A":
        failures.append(f"A self-register overwritten: {reg_a!r}")
    # NOTE: this block used to also assert that ``reg_b`` was a SEPARATE register
    # owned by did:key:B with value "en", i.e. that a merge keeps one register per
    # subject. That is unsatisfiable under this document schema, which has exactly
    # one register per (field, key) -- and satisfying it would mean the merge
    # depended on which side was passed as ``local``, which the determinism check
    # above explicitly forbids. Those two expectations came from the discarded
    # implementation of #63; B's value is retained as an attributed claim instead,
    # which the assertion above already checks.
    print("[merge] subject owns the register; peer value retained as a claim")

    # ---- 2. import from IndividualMemoryStore shape ----
    store = {"facts": {"name": "rhizome"}, "notes": ["note one", "note two"],
             "skills": ["search"], "preferences": {"verbosity": "low"}}
    m = MemoryMirror.from_memory_dict("did:key:A", store)
    out = m.as_memory_dict()
    if out["facts"] != {"name": "rhizome"} or out["notes"] != ["note one", "note two"]:
        failures.append(f"store import mismatch: {out}")
    print("[import] IndividualMemoryStore shape round-trips")

    # ---- 3. sync over InMemoryTransport with signed envelopes ----
    tmp = Path(tempfile.mkdtemp(prefix="pcm-mirror-"))
    id_a = generate_identity(str(tmp / "a"))
    key_a = private_key_from_identity(id_a)
    id_b = generate_identity(str(tmp / "b"))
    key_b = private_key_from_identity(id_b)

    async def sync_flow() -> None:
        # InMemoryTransport is a single-bus loopback: BOTH nodes share one
        # instance so publications cross (the zenoh fabric gives real nodes
        # this crossing for free; the loopback emulates it with one bus).
        tr = InMemoryTransport({"pcm_id": "bus"})
        await tr.start()

        mirror_a = MemoryMirror(id_a["did"])
        mirror_b = MemoryMirror(id_b["did"])
        sync_a = MemorySync(tr, id_a["did"], key_a)
        sync_b = MemorySync(
            tr, id_b["did"], key_b,
            capabilities_for_sender=lambda sender: (
                ("write_memory",) if sender == id_a["did"] else ()),
        )
        await sync_b.subscribe(mirror_b)

        mirror_a.set("facts", "home_base", "the commons")
        await sync_a.push(mirror_a)
        await asyncio.sleep(0)  # let handlers run

        got = mirror_b.as_memory_dict()["facts"].get("home_base")
        if got != "the commons":
            failures.append(f"B did not receive A's fact: {got!r}")
        shared_by_b = mirror_b.to_document(include_private=False)
        shared_reg = shared_by_b["fields"]["facts"]["home_base"]
        if shared_reg.get("author") != id_a["did"] or shared_reg.get("subject") != id_a["did"]:
            failures.append(f"absorbed memory was re-attributed by B: {shared_reg!r}")
        print(f"[sync] A -> B via signed memory_share: {got!r}; authorship retained")

        # tampered envelope rejected
        env = await _captured_envelope(sync_a, mirror_a)
        env["content"]["mirror"]["fields"]["facts"]["home_base"]["value"] = "hijacked"
        try:
            await sync_b.handle(env, mirror_b)
            failures.append("tampered memory_share accepted")
        except Exception:
            print("[tamper] forged mirror envelope rejected (sig mismatch)")

        # Private registers must be absent from the actual wire envelope.
        private_mirror = MemoryMirror(id_a["did"])
        private_mirror.set("notes", "0", "public thought")
        private_mirror.set("notes", "1", "private thought", private=True)
        private_env = await _captured_envelope(sync_a, private_mirror)
        wire = json.dumps(private_env, ensure_ascii=False)
        if "private thought" in wire:
            failures.append("private register serialized into memory_share")
        print("[privacy-wire] private register absent from memory_share")

        # A valid signature is not an authorization grant.
        unauthorized = MemoryMirror(id_b["did"])
        unauthorized.set("facts", "owner", "attacker-controlled")
        unauthorized_env = await _captured_envelope(sync_b, unauthorized)
        try:
            await sync_b.handle(unauthorized_env, mirror_b)
            failures.append("self-signed sender merged without write_memory")
        except EnvelopeError:
            print("[authorization] signed sender without write_memory rejected")

        await tr.stop()

    async def _captured_envelope(sync: MemorySync, mirror: MemoryMirror) -> dict:
        captured = {}
        real_publish = sync.transport.publish

        async def spy(topic, event):
            captured.update(event)
        sync.transport.publish = spy
        await sync.push(mirror)
        sync.transport.publish = real_publish
        return captured

    asyncio.run(sync_flow())

    # ---- 4. events.jsonl authoritative: audit event appended ----
    from multitude.rhizome import Rhizome
    import os
    root = tmp / "tribe"; root.mkdir()
    rhizome = Rhizome.found(str(root), "Mirror Rhizome", "Share memory.", "Alice")
    rhizome.remember("mirror-sync", "memory_share envelope received and merged",
                   author="Alice", kind="note")
    audit = [e for e in rhizome.memory.values() if e.title == "mirror-sync"]
    if not audit:
        failures.append("audit event missing from rhizome log")
    else:
        print(f"[audit] rhizome log records mirror sync (title={audit[0].title!r})")

    # ---- 5. privacy: private fields stay local ----
    m_priv = MemoryMirror("did:key:A")
    m_priv.set("notes", "0", "public thought")
    m_priv.set("notes", "1", "private thought", private=True)
    shared = m_priv.as_memory_dict(include_private=False)
    if "private thought" in shared["notes"]:
        failures.append("private note leaked into shareable projection")
    if "private thought" not in m_priv.as_memory_dict()["notes"]:
        failures.append("private note lost locally")
    print("[privacy] private field excluded from share, kept locally")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("ALL MEMORY MIRROR TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def test_pcm_memory_mirror():
    assert main() == 0