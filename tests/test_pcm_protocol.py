# -*- coding: utf-8 -*-
"""Phase 0 protocol tests — NETWORKING_STACK.md §7 Phase 0 test criteria:

1. A signed envelope round-trips dict → JSON → dict with signature
   verification.
2. Tampered payloads are rejected (any field flip breaks the signature).
3. DID binding verifies (stored DID derives from stored public key).
4. Relay policy: private content is flagged unsafe to relay.

Run: python3 tests/test_pcm_protocol.py  (or via pytest)
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.pcm import (ACTOR_KINDS, ENVELOPE_TYPES, Envelope,
                           EnvelopeError, generate_identity, load_identity,
                           verify_did_binding)
from multitude.pcm.identity import private_key_from_identity


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="pcm-protocol-"))
    failures: list[str] = []

    # ---- 1. DID identity generation + binding ----
    identity = generate_identity(tmp)
    again = generate_identity(tmp)  # idempotent
    if again["did"] != identity["did"]:
        failures.append("generate_identity not idempotent")
    if not verify_did_binding(identity):
        failures.append("stored DID does not bind to stored public key")
    did = identity["did"]
    print(f"[identity] {did}")

    # ---- 2. envelope create + sign ----
    env = Envelope.create(
        "layer_recorded", did, did,  # self-addressed node test
        {"layer": "psychic", "field": "attention", "value": 3},
        actor_kind="cyborg", capabilities=["read_memory", "propose"],
    )
    if env.type not in ENVELOPE_TYPES or env.actor_kind not in ACTOR_KINDS:
        failures.append("vocabulary check failed")
    env.sign(private_key_from_identity(identity), did)
    if not env.sig.startswith("ed25519:"):
        failures.append("signature not stored")
    print(f"[envelope] id={env.id} type={env.type} sig={env.sig[:20]}...")

    # ---- 2b. privacy invariant: private content refused at construction ----
    # (spec rule 4: private data never leaves its node unless published)
    try:
        Envelope.create(
            "layer_recorded", did, did,
            {"layer": "psychic", "field": "attention", "value": 3,
             "private": True},
            actor_kind="cyborg",
        )
        failures.append("private content serialized into an outbound envelope")
    except EnvelopeError:
        pass
    print("[privacy] private-content envelope refused at construction")

    # ---- 3. round-trip: dict -> JSON -> dict -> verify ----
    wire = env.model_dump(by_alias=True)
    wire_json = json.dumps(wire, ensure_ascii=False)
    revived = Envelope.model_validate(json.loads(wire_json))
    try:
        revived.verify()
    except EnvelopeError as e:
        failures.append(f"round-trip verification failed: {e}")
    if revived.id != env.id or revived.content != env.content:
        failures.append("round-trip field drift")
    print(f"[round-trip] json={len(wire_json)}B verified OK")

    # ---- 4. tampered payload rejected (spec §7 Phase 0 criterion) ----
    # each variant changes exactly one field of the signed wire form
    tampered_variants = [
        {**wire, "content": {**wire["content"], "value": 5}},   # value 3->5
        {**wire, "ts": "2030-01-01T00:00:00Z"},                 # replay
        {**wire, "from": "did:key:z1Attacker"},                 # spoofed sender
        {**wire, "type": "say"},                                # type swap
        {**wire, "capabilities": ["spend_money"]},              # privilege escalation
    ]
    for variant in tampered_variants:
        forged = Envelope.model_validate(variant)
        try:
            forged.verify()
            failures.append(
                f"tampered envelope ACCEPTED — signature check broken: "
                f"{ {k: v for k, v in variant.items() if wire.get(k) != v} }")
        except EnvelopeError:
            pass
    print("[tamper] content/ts/from/type/capabilities mutations all rejected")

    # ---- 5. unsigned envelope rejected ----
    try:
        unsigned = Envelope.model_validate({**wire, "sig": ""})
        unsigned.verify()
        failures.append("unsigned envelope accepted")
    except EnvelopeError:
        pass

    # ---- 6. wrong signer key rejected ----
    other = generate_identity(tmp / "other-node")
    try:
        wrong_env = Envelope.model_validate(wire)
        wrong_env.sign(private_key_from_identity(other), did)
        failures.append("signing with mismatched key succeeded")
    except EnvelopeError:
        pass

    # ---- 7. relay policy (spec §3 rule 3 + rule 4) ----
    # Public envelopes relay; private content never reaches an envelope
    # (blocked at construction — asserted in 2b), and the relay guard
    # stays correct if a tamper path ever re-injects the marker.
    if not env.relay_safe():
        failures.append("public envelope flagged private")
    public_env = Envelope.create("heartbeat", did, did, {"uptime": 1})
    public_env.sign(private_key_from_identity(identity), did)
    if not public_env.relay_safe():
        failures.append("public heartbeat flagged private")
    smuggled = Envelope.model_validate({
        "pcm": "1", "id": "pcm_x", "type": "memory_share",
        "from": did, "to": did, "ts": "2026-09-06T00:00:00Z",
        "interface": "jsonl", "actor_kind": "ai", "capabilities": [],
        "content": {"private": True, "secret": "leak"}, "sig": ""})
    if smuggled.relay_safe():
        failures.append("relay_safe() true for private content")
    print("[relay] public passes; private refused at construction + relay guard")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("ALL PCM PROTOCOL TESTS PASSED")
    print(f"(artifacts in {tmp})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# pytest wrapper (canonical suite collects this)
def test_pcm_protocol():
    assert main() == 0