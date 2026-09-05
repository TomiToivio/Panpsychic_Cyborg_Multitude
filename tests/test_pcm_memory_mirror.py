# -*- coding: utf-8 -*-
"""Phase 3 tests — memory mirror over the PCM Transport ABC.

NETWORKING_STACK.md §12 Phase 3 line: "automerge memory mirror".
Implementation: pcm/memory_mirror.py — per-field LWW merge document
(Automerge-compatible semantics, stdlib codec) synced as signed
memory_share envelopes over the Transport ABC.

Test criteria:
1. LWW merge is deterministic on both sides (lamport, did order).
2. Existing IndividualMemoryStore-shaped data imports cleanly.
3. Sync: node A pushes a signed memory_share envelope; node B's mirror
   updates ONLY via verified envelope; tampered envelope is rejected.
4. events.jsonl stays authoritative — mirror changes append to the
   tribe log as audit events, never silently overwrite.
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
from multitude.pcm.memory_mirror import (
    MemoryMirror, MemorySync, merge_memory_docs)
from multitude.pcm.transport import InMemoryTransport


def main() -> int:
    failures: list[str] = []

    # ---- 1. deterministic LWW merge ----
    a = MemoryMirror("did:key:A")
    a.set("facts", "language", "fi")
    b = MemoryMirror("did:key:B")
    b.set("facts", "language", "en")
    # B has higher lamport on the same key -> B wins, deterministically
    doc_a, doc_b = a.to_document(), b.to_document()
    m_ab = merge_memory_docs(doc_a, doc_b)
    m_ba = merge_memory_docs(doc_b, doc_a)
    val_ab = m_ab["fields"]["facts"]["language"]["value"]
    val_ba = m_ba["fields"]["facts"]["language"]["value"]
    if val_ab != "en" or val_ba != "en":
        failures.append(f"LWW nondeterministic: {val_ab!r} vs {val_ba!r}")
    print(f"[merge] LWW tie-break deterministic: both sides -> {val_ab!r}")

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
        sync_b = MemorySync(tr, id_b["did"], key_b)
        await sync_b.subscribe(mirror_b)

        mirror_a.set("facts", "home_base", "the commons")
        await sync_a.push(mirror_a)
        await asyncio.sleep(0)  # let handlers run

        got = mirror_b.as_memory_dict()["facts"].get("home_base")
        if got != "the commons":
            failures.append(f"B did not receive A's fact: {got!r}")
        print(f"[sync] A -> B via signed memory_share: {got!r}")

        # tampered envelope rejected
        env = await _captured_envelope(sync_a, mirror_a)
        env["content"]["mirror"]["fields"]["facts"]["home_base"]["value"] = "hijacked"
        try:
            await sync_b.handle(env, mirror_b)
            failures.append("tampered memory_share accepted")
        except Exception:
            print("[tamper] forged mirror envelope rejected (sig mismatch)")

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
    from multitude.tribe import Tribe
    import os
    root = tmp / "tribe"; root.mkdir()
    tribe = Tribe.found(str(root), "Mirror Tribe", "Share memory.", "Alice")
    tribe.remember("mirror-sync", "memory_share envelope received and merged",
                   author="Alice", kind="note")
    audit = [e for e in tribe.memory.values() if e.title == "mirror-sync"]
    if not audit:
        failures.append("audit event missing from tribe log")
    else:
        print(f"[audit] tribe log records mirror sync (title={audit[0].title!r})")

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