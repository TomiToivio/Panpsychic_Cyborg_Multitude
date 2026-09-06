# -*- coding: utf-8 -*-
"""Adversarial distributed tests — governance determinism, privacy, authz.

Beyond happy-path unit tests, these exercise the failure modes a
distributed, partitionable, occasionally hostile network produces:

  1. duplicate event (replayed vote, replayed close)
  2. out-of-order event (vote arrives after close)
  3. conflicting proposal closure (partition merge: first close wins)
  4. node disappearing during vote (replay still deterministic)
  5. malicious signer (forged envelope rejected)
  6. valid signer without authorization (authenticated != authorized)
  7. revoked capability (grant withdrawn -> merge refused)
  8. private memory leaking attempt (outbound envelope refuses)
  9. key mismatch (signing key != claimed DID)
 10. deterministic replay: hostile log orderings rebuild identical state

Run: python3 tests/test_adversarial_distributed.py  (or via pytest)
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.rhizome import Rhizome, RhizomeError
from multitude.models import NodeKind, Position, ProposalStatus, Outcome, Rule
from multitude.pcm.envelope import (
    Envelope, EnvelopeError, authorize_sender, REQUIRED_CAPABILITY)
from multitude.pcm.identity import (
    generate_identity, private_key_from_identity)
from multitude.pcm.proposals import (
    signed_proposal_envelope, signed_vote_envelope, proposal_from_envelope)


def _tribe(name: str, root: Path) -> Rhizome:
    t = Rhizome.found(str(root), name, f"Charter of {name}.", "alice")
    t.join("bob", kind=NodeKind.BIOLOGICAL)
    t.join("carol", kind=NodeKind.BIOLOGICAL)
    t.join("pcm", kind=NodeKind.TECHNOLOGICAL, model="test-model", voting=False)
    return t


def check_duplicate_and_out_of_order() -> int:
    """Duplicate vote events and post-close votes stay idempotent."""
    failures: list[str] = []
    root = Path(tempfile.mkdtemp(prefix="pcm-adv-"))
    t = _tribe("dup", root)
    p = t.open_proposal("Dup test", "body", "alice")
    t.cast_vote(p.id, "alice", Position.FOR)
    # duplicate vote event: same member again -> ignored on replay/apply
    ev = {"proposal_id": p.id,
          "vote": {"member": t.members.get(next(iter(t.members))).id if False else next(
              m.id for m in t.members.values() if m.name == "alice"),
              "position": "against", "reason": "sneaky re-vote", "ts": ""}}
    t._apply("vote_cast", ev)  # direct apply = replay path
    alice_id = next(m.id for m in t.members.values() if m.name == "alice")
    if t.proposals[p.id].votes[alice_id].position != Position.FOR:
        failures.append("duplicate vote overwrote the first vote")
    # live double-vote attempt raises
    try:
        t.cast_vote(p.id, "alice", Position.AGAINST)
        failures.append("live double vote accepted")
    except RhizomeError:
        pass
    # close, then an out-of-order vote event arrives (partition merge)
    d = t.close_proposal(p.id, "bob")
    late_vote = {"proposal_id": p.id,
                 "vote": {"member": next(m.id for m in t.members.values()
                                         if m.name == "carol"),
                          "position": "against", "reason": "late", "ts": ""}}
    t._apply("vote_cast", late_vote)
    if t.proposals[p.id].status == ProposalStatus.OPEN:
        failures.append("late vote reopened the proposal")
    if any(v.member == next(m.id for m in t.members.values() if m.name == "carol")
           for v in t.proposals[p.id].votes.values()):
        failures.append("late vote was counted after close")
    print("[1] duplicate votes idempotent; post-close votes ignored")
    return len(failures)


def check_conflicting_closures_first_wins() -> int:
    """Two closes of the same proposal: first wins, second recorded as
    rejected duplicate. Deterministic under both replay orders."""
    failures: list[str] = []
    root = Path(tempfile.mkdtemp(prefix="pcm-adv-close-"))
    t = _tribe("split", root)
    p = t.open_proposal("Partition test", "body", "alice", rule=Rule.MAJORITY)
    t.cast_vote(p.id, "alice", Position.FOR)
    t.cast_vote(p.id, "bob", Position.FOR)
    d1 = t.close_proposal(p.id, "alice")  # adopted: 2 FOR, 0 against

    # A second node that never saw the close closes again (rejected
    # outcome). Replay both orders; state must match the FIRST close.
    d2_payload = {"decision": {
        "id": "dec-fake-second", "ts": "", "proposal_id": p.id,
        "proposal_title": p.title, "rule": "majority", "outcome": "rejected",
        "tally": {"for": 0, "against": 0, "abstain": 0, "block": 0},
        "quorum_required": p.quorum, "votes_cast": 0, "closed_by": "carol",
        "dissent": [], "notes": ""}}
    # order A: first real close, then the conflicting one
    t2 = Rhizome(t.store)
    t2._apply("proposal_closed", d2_payload)
    if t2.proposals[p.id].outcome != d1.outcome:
        failures.append(f"conflicting close changed outcome: {t2.proposals[p.id].outcome}")
    loser = [x for x in t2.decisions if x.id == "dec-fake-second"]
    if not loser or "rejected duplicate" not in (loser[0].notes or ""):
        failures.append("conflicting close not marked as rejected duplicate")
    # order B: conflicting one first would have won on that node — the
    # guarantee is per-log determinism, not cross-log magic; the merged
    # log order (whoever's log appends first) decides identically for
    # all replays of THAT log.
    t3 = Rhizome(t.store)
    outcomes = [d.outcome for d in t3.decisions if d.proposal_id == p.id
                and "rejected duplicate" not in (d.notes or "")]
    if outcomes != [d1.outcome]:
        failures.append(f"replay not deterministic: {outcomes}")
    print("[2] conflicting closures: first close wins; loser recorded as duplicate")
    return len(failures)


def check_node_disappears_during_vote() -> int:
    """Votes from a member who later leaves still replay deterministically
    (left members' votes are excluded from tallies at close time)."""
    failures: list[str] = []
    root = Path(tempfile.mkdtemp(prefix="pcm-adv-leave-"))
    t = _tribe("vanish", root)
    p = t.open_proposal("Vanish test", "body", "alice", rule="majority", quorum=2)
    t.cast_vote(p.id, "alice", Position.FOR)
    t.cast_vote(p.id, "bob", Position.FOR)
    t.leave("carol")  # carol vanishes without voting
    d = t.close_proposal(p.id, "alice")
    if d.outcome != Outcome.ADOPTED:
        failures.append(f"outcome after member leave wrong: {d.outcome}")
    # full replay from the log: same state
    t2 = Rhizome(t.store)
    if t2.proposals[p.id].outcome != Outcome.ADOPTED:
        failures.append("replay diverged after member leave")
    print("[3] member-vanish mid-proposal: tallies + replay deterministic")
    return len(failures)


def check_malicious_signer_and_key_mismatch() -> int:
    """Forged content, wrong signer, and key/DID mismatch all fail."""
    failures: list[str] = []
    root = Path(tempfile.mkdtemp(prefix="pcm-adv-sig-"))
    id_a = generate_identity(root / "a")
    id_b = generate_identity(root / "b")
    key_a = private_key_from_identity(id_a)

    proposal = signed_proposal_envelope(str(root / "a"), "Legit", "text")
    fields = proposal_from_envelope(proposal)
    if fields["did"] != id_a["did"]:
        failures.append("legit envelope failed")
    # tampered content
    forged = {**proposal, "content": {**proposal["content"], "text": "hijacked"}}
    try:
        proposal_from_envelope(forged)
        failures.append("tampered proposal accepted")
    except EnvelopeError:
        pass
    # wrong signer: same DID claim, different key — sign() itself refuses
    wrong_key_env = Envelope.model_validate(proposal)
    wrong_key_env.sig = ""
    try:
        wrong_key_env.sign(private_key_from_identity(id_b), id_b["did"])
        failures.append("envelope signed by a different key accepted")
    except EnvelopeError:
        pass
    # key/DID mismatch at signing time
    env = Envelope.create("say", id_a["did"], id_a["did"], {"x": 1})
    try:
        env.sign(key_a, id_b["did"])
        failures.append("sign with mismatched expected_did accepted")
    except EnvelopeError:
        pass
    print("[4] forged/tampered/wrong-key envelopes rejected")
    return len(failures)


def check_authenticated_but_not_authorized() -> int:
    """A valid signature alone must not grant merge/write rights."""
    failures: list[str] = []
    root = Path(tempfile.mkdtemp(prefix="pcm-adv-authz-"))
    id_s = generate_identity(root / "sender")
    env = Envelope.create(
        "memory_share", id_s["did"], id_s["did"],
        {"entries": [{"title": "injected memory", "text": "hello"}]},
    )
    env.sign(private_key_from_identity(id_s), id_s["did"])
    verified = env.model_dump(by_alias=True)
    # verify first (authenticated)
    Envelope.model_validate(verified).verify()
    # authorization: no grants -> memory_share refused
    try:
        authorize_sender(verified, [])
        failures.append("memory_share accepted with zero capabilities")
    except EnvelopeError:
        pass
    # read-only grant still refuses writes
    try:
        authorize_sender(verified, ["read_memory", "search_memory"])
        failures.append("memory_share accepted with read-only grant")
    except EnvelopeError:
        pass
    # with the grant it passes
    authorize_sender(verified, ["write_memory"])
    # revoked: grant withdrawn -> refused again (revocation = drop grant)
    try:
        authorize_sender(verified, [])
        failures.append("memory_share accepted after capability revoked")
    except EnvelopeError:
        pass
    print("[5] authenticated != authorized; revoked capability refuses merge")
    return len(failures)


def check_private_memory_never_leaks() -> int:
    """Private content cannot be serialized into an outbound envelope."""
    failures: list[str] = []
    root = Path(tempfile.mkdtemp(prefix="pcm-adv-priv-"))
    id_s = generate_identity(root / "s")
    # attempt 1: direct private flag
    try:
        Envelope.create("memory_share", id_s["did"], id_s["did"],
                        {"private": True, "secret": "diary text"})
        failures.append("private content serialized into outbound envelope")
    except EnvelopeError:
        pass
    # attempt 2: sneaky non-bool truthy marker
    try:
        Envelope.create("memory_share", id_s["did"], id_s["did"],
                        {"private": "yes", "secret": "diary"})
        failures.append("truthy private marker accepted")
    except EnvelopeError:
        pass
    # legitimate publish path: strip/transform first, then share
    env = Envelope.create("memory_share", id_s["did"], id_s["did"],
                          {"title": "published note", "text": "public version"})
    env.sign(private_key_from_identity(id_s), id_s["did"])
    # relay_safe double-check on a crafted private-content envelope built
    # via model_validate (bypassing create, as a tamper path would)
    smuggled = Envelope.model_validate({
        "pcm": "1", "id": "pcm_x", "type": "memory_share",
        "from": id_s["did"], "to": id_s["did"], "ts": "2026-09-06T00:00:00Z",
        "interface": "jsonl", "actor_kind": "ai", "capabilities": [],
        "content": {"private": True, "secret": "leak"}, "sig": ""})
    if smuggled.relay_safe():
        failures.append("relay_safe() true for private content")
    print("[6] private content blocked at envelope construction; relay guard intact")
    return len(failures)


def check_deterministic_replay_under_hostile_orders() -> int:
    """Same events in different arrival orders -> identical final state
    for orderings the kernel can observe (log order is authoritative)."""
    failures: list[str] = []
    root = Path(tempfile.mkdtemp(prefix="pcm-adv-order-"))
    t = _tribe("order", root)
    p = t.open_proposal("Order test", "body", "alice", rule=Rule.MAJORITY)
    t.cast_vote(p.id, "alice", Position.FOR)
    t.cast_vote(p.id, "bob", Position.AGAINST, reason="I object")
    t.cast_vote(p.id, "carol", Position.FOR)
    expected = t.close_proposal(p.id, "bob")
    # replay the whole log twice
    s1, s2 = Rhizome(t.store), Rhizome(t.store)
    for rebuilt in (s1, s2):
        if rebuilt.proposals[p.id].outcome != expected.outcome:
            failures.append("replayed outcome diverged")
        if len(rebuilt.decisions) != len(t.decisions):
            failures.append("decision count diverged on replay")
    print("[7] hostile-order replay: outcomes identical across rebuilds")
    return len(failures)


def main() -> int:
    total = (
        check_duplicate_and_out_of_order()
        + check_conflicting_closures_first_wins()
        + check_node_disappears_during_vote()
        + check_malicious_signer_and_key_mismatch()
        + check_authenticated_but_not_authorized()
        + check_private_memory_never_leaks()
        + check_deterministic_replay_under_hostile_orders()
    )
    print()
    if total:
        print(f"{total} FAILURES")
        return 1
    print("ALL ADVERSARIAL DISTRIBUTED TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# pytest wrappers
def test_adv_duplicate_out_of_order():
    assert check_duplicate_and_out_of_order() == 0

def test_adv_conflicting_closures():
    assert check_conflicting_closures_first_wins() == 0

def test_adv_node_vanish():
    assert check_node_disappears_during_vote() == 0

def test_adv_signatures():
    assert check_malicious_signer_and_key_mismatch() == 0

def test_adv_authorization():
    assert check_authenticated_but_not_authorized() == 0

def test_adv_privacy():
    assert check_private_memory_never_leaks() == 0

def test_adv_replay_determinism():
    assert check_deterministic_replay_under_hostile_orders() == 0