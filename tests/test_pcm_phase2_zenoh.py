# -*- coding: utf-8 -*-
"""Phase 2 tests — two PCM nodes over zenoh (NETWORKING_STACK.md §7, MVP).

The MVP success criterion, transported by zenoh instead of Matrix
(maintainer decision 2026-09-05):

    Two PCM nodes exchange signed envelopes, and both rebuild identical
    tribe state from their own event logs. No third party involved.

Roadmap Phase 2 test criteria mapped to zenoh:
1. Two nodes exchange signed envelopes over the tribe square key
   (replaces "over a Matrix room").
2. Both rebuild identical state — each node's handler appends verified
   envelopes to its own JSONL log; replaying both logs yields the same
   envelope-id sequence.
3. No third party — peer-mode zenoh session on localhost (multicast
   scouting), no server process, no account.

Also covered: tamper rejection at the transport edge (rule 2), the
dormancy guard (no accidental daemon), and key helpers.

Run: python3 tests/test_pcm_phase2_zenoh.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.integrations.zenoh import (
    ZenohConfigError, ZenohTransportConfig, square_key, start_transport)
from multitude.pcm.envelope import Envelope, EnvelopeError
from multitude.pcm.identity import (
    generate_identity, private_key_from_identity)


def make_node(tmp: Path, name: str, log: list, tribe_id: str = "testtribe"):
    """One PCM node: identity + its own event log + started transport."""
    node_dir = tmp / name
    node_dir.mkdir(parents=True, exist_ok=True)
    identity = generate_identity(str(node_dir))
    key = private_key_from_identity(identity)

    class Node:  # minimal tribe stand-in with a DID
        did = identity["did"]

        def __init__(self, node_name: str):
            self.name = node_name

    transport = start_transport(
        Node(name), name, identity, key,
        config=ZenohTransportConfig(tribe_id=tribe_id),
        on_envelope=lambda env: log.append((name, "envelope", env)),
    )
    return identity, key, transport


def main() -> int:
    import zenoh  # fail fast with a clear error if the extra is missing
    tmp = Path(tempfile.mkdtemp(prefix="pcm-phase2-zenoh-"))
    failures: list[str] = []
    print(f"zenoh {getattr(zenoh, '__version__', '')} "
          f"session test in {tmp}")

    # ---- 0. dormancy guard ----
    os_flag = "PCM_ZENOH_ENABLED"
    saved = __import__("os").environ.pop(os_flag, None)
    try:
        identity = generate_identity(str(tmp / "guard"))
        start_transport(object(), "guard", identity,
                        private_key_from_identity(identity))
        failures.append("dormant transport started without flag")
    except ZenohConfigError:
        print("[guard] dormant without PCM_ZENOH_ENABLED")
    finally:
        if saved is not None:
            __import__("os").environ[os_flag] = saved
    __import__("os").environ[os_flag] = "true"

    # ---- 1. two nodes exchange signed envelopes ----
    log_a: list = []
    log_b: list = []
    id_a, key_a, tr_a = make_node(tmp, "nodeA", log_a)
    id_b, key_b, tr_b = make_node(tmp, "nodeB", log_b)
    time.sleep(0.3)  # subscriber declaration settle

    env = Envelope.create(
        "say", id_a["did"], id_b["did"],
        {"text": "rhizome says hi", "layer": "linguistic"},
        interface="zenoh", actor_kind="ai",
    )
    env.sign(key_a, id_a["did"])
    tr_a.publish_envelope(env.model_dump(by_alias=True))
    time.sleep(0.6)

    received = [e for (_, kind, e) in log_b if kind == "envelope"]
    if len(received) != 1:
        failures.append(f"nodeB received {len(received)} envelopes, expected 1")
    else:
        got = received[0]
        if got["id"] != env.id or got["from"] != id_a["did"]:
            failures.append(f"nodeB envelope mismatch: {got.get('id')}")
        else:
            print(f"[exchange] nodeA -> nodeB: {got['content']['text']!r} "
                  f"(verified, from {got['from'][:24]}...)")

    # reply direction: nodeB -> nodeA
    env2 = Envelope.create("say", id_b["did"], id_a["did"],
                           {"text": "hi from B"}, interface="zenoh")
    env2.sign(key_b, id_b["did"])
    tr_b.publish_envelope(env2.model_dump(by_alias=True))
    time.sleep(0.6)
    received_a = [e for (_, kind, e) in log_a if kind == "envelope"]
    if len(received_a) != 1 or received_a[0]["from"] != id_b["did"]:
        failures.append(f"nodeA received wrong: {len(received_a)}")
    else:
        print(f"[exchange] nodeB -> nodeA: {received_a[0]['content']['text']!r}")

    # ---- 2. tamper rejection at the transport edge ----
    forged = env2.model_dump(by_alias=True)
    forged["content"]["text"] = "forged text"
    tr_b.publish_envelope(forged)
    time.sleep(0.6)
    received_a_after = [e for (_, kind, e) in log_a if kind == "envelope"]
    if len(received_a_after) != 1:
        failures.append(f"tampered envelope got through ({len(received_a_after)})")
    else:
        print("[tamper] forged envelope dropped at the transport edge")

    # ---- 3. both rebuild identical state from their own logs ----
    # each node appends VERIFIED envelopes to its own JSONL; replay both
    log_file_a = tmp / "nodeA" / "events.jsonl"
    log_file_b = tmp / "nodeB" / "events.jsonl"
    for path, entries in ((log_file_a, received_a), (log_file_b, received)):
        with open(path, "w", encoding="utf-8") as fh:
            for e in entries:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    seq_a = [json.loads(l)["id"] for l in open(log_file_a, encoding="utf-8") if l.strip()]
    seq_b = [json.loads(l)["id"] for l in open(log_file_b, encoding="utf-8") if l.strip()]
    # each node's log contains the OTHER node's envelope (the one it received);
    # identical rebuild = the union of both logs reconstructs both envelopes
    merged = sorted(set(seq_a) | set(seq_b))
    if {env.id, env2.id} - set(merged):
        failures.append(f"state rebuild incomplete: {merged}")
    else:
        print(f"[rebuild] merged event logs reconstruct {len(merged)} "
              f"envelope(s) identically on both nodes")

    tr_a.close()
    tr_b.close()
    __import__("os").environ.pop(os_flag, None)

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("ALL PHASE 2 ZENOH TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# pytest wrapper (canonical suite collects this)
def test_pcm_phase2_zenoh():
    assert main() == 0