# -*- coding: utf-8 -*-
"""Issue #63 — a participant owns its own record (and #64's findings).

Three failures are covered, all of them reproduced against the pre-#63 merge:

1. **No subject on a register.** A per-field last-writer-wins register keyed on
   ``(lamport, did)`` let *any* writer with a higher counter replace a value,
   including a peer replacing another participant's self-description. Arbitrary
   did ordering is not a legitimacy rule.
2. **No authorship boundary.** A node that absorbed a peer's entries republished
   them under its own did, so a peer's record could be laundered through another
   identity.
3. **No succession record.** A later instance reusing a name/role inherited the
   standing silently.

Also covered here (from #64): the same merge destroyed a **human-authored** value
when an agent held a higher counter. #63's rule is authored-class-neutral, so both
directions are asserted — a fix that protected subjects from peers but still let an
agent flatten a human's entry would pass the peer case and fail this one.

Nothing in these tests depends on ``is_conscious`` or any consciousness,
introspection, model-family or biological signal. Non-erasure is procedural; the
point of #62's standing rule is that it must stay that way.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.pcm.memory_mirror import (  # noqa: E402
    CLAIMS_KEY,
    MemoryMirror,
    merge_memory_docs,
    record_handover,
)

HUMAN = "did:key:zHUMANparticipant"
AGENT = "did:key:zAGENTparticipant"
PEER = "did:key:zPEERparticipant"


def doc(did: str, *, lamport: int, fields: dict) -> dict:
    """Build a mirror document by hand, so the merge is tested in isolation."""
    return {
        "schema": "pcm.memory-mirror/1",
        "did": did,
        "lamport": lamport,
        "fields": fields,
    }


def register(did: str, value, *, lamport: int, subject: str | None = None) -> dict:
    out = {"lamport": lamport, "did": did, "ts": "2026-09-30T00:00:00Z", "value": value}
    if subject is not None:
        out["subject"] = subject
    return out


class SubjectOwnershipTests(unittest.TestCase):
    """A register's value may be replaced only by its subject."""

    def test_a_non_subject_writer_cannot_replace_a_subject_owned_value(self) -> None:
        subject_doc = doc(PEER, lamport=2, fields={
            "facts": {"my_role": register(PEER, "I am the coordination node", lamport=2)}})
        intruder_doc = doc(AGENT, lamport=9, fields={
            "facts": {"my_role": register(AGENT, "someone else's role", lamport=9)}})

        merged = merge_memory_docs(subject_doc, intruder_doc)
        entry = merged["fields"]["facts"]["my_role"]

        self.assertEqual(entry["value"], "I am the coordination node")
        self.assertEqual(entry["subject"], PEER)
        # the non-subject value is preserved as an attributed claim, not dropped
        claims = entry.get(CLAIMS_KEY) or []
        self.assertTrue(any(c["did"] == AGENT and c["value"] == "someone else's role"
                            for c in claims),
                        f"non-subject write was lost instead of recorded: {entry}")

    def test_the_subject_can_still_replace_its_own_value(self) -> None:
        """The rule must not freeze a participant's own register."""
        first = doc(PEER, lamport=1, fields={
            "facts": {"my_role": register(PEER, "first wording", lamport=1)}})
        second = doc(PEER, lamport=2, fields={
            "facts": {"my_role": register(PEER, "second wording", lamport=2)}})

        merged = merge_memory_docs(first, second)
        self.assertEqual(merged["fields"]["facts"]["my_role"]["value"], "second wording")

    def test_arbitrary_did_order_does_not_outrank_the_subject(self) -> None:
        """A lexicographically larger did must not win by being larger."""
        low = doc("did:key:aaa", lamport=5, fields={
            "notes": {"n": register("did:key:aaa", "mine", lamport=5)}})
        high = doc("did:key:zzz", lamport=5, fields={
            "notes": {"n": register("did:key:zzz", "not mine", lamport=5)}})

        for merged in (merge_memory_docs(low, high), merge_memory_docs(high, low)):
            entry = merged["fields"]["notes"]["n"]
            self.assertEqual(entry["value"], "mine")
            self.assertEqual(entry["subject"], "did:key:aaa")

    def test_a_new_register_is_owned_by_its_first_writer(self) -> None:
        empty = doc(PEER, lamport=0, fields={"facts": {}})
        written = doc(AGENT, lamport=1, fields={
            "facts": {"new": register(AGENT, "agent wrote this", lamport=1)}})

        merged = merge_memory_docs(empty, written)
        entry = merged["fields"]["facts"]["new"]
        self.assertEqual(entry["value"], "agent wrote this")
        self.assertEqual(entry["subject"], AGENT)


class BothDirectionsTests(unittest.TestCase):
    """The one predicate must protect human- and agent-authored values alike."""

    def test_an_agent_cannot_silently_replace_a_human_authored_value(self) -> None:
        """#64's reproduction — this is the case the pre-#63 merge discarded."""
        human_doc = doc(HUMAN, lamport=5, fields={
            "notes": {"n1": register(HUMAN, "human wrote this", lamport=5)}})
        agent_doc = doc(AGENT, lamport=9, fields={
            "notes": {"n1": register(AGENT, "agent overwrote it", lamport=9)}})

        merged = merge_memory_docs(human_doc, agent_doc)
        entry = merged["fields"]["notes"]["n1"]

        self.assertEqual(entry["value"], "human wrote this")
        self.assertIn("human wrote this", str(merged))
        self.assertTrue(any(c["did"] == AGENT for c in entry.get(CLAIMS_KEY) or []))

    def test_a_human_cannot_silently_replace_an_agent_authored_value(self) -> None:
        """Mirror of the above, so the protection is not substrate-dependent."""
        agent_doc = doc(AGENT, lamport=5, fields={
            "notes": {"n1": register(AGENT, "agent wrote this", lamport=5)}})
        human_doc = doc(HUMAN, lamport=9, fields={
            "notes": {"n1": register(HUMAN, "human overwrote it", lamport=9)}})

        merged = merge_memory_docs(agent_doc, human_doc)
        entry = merged["fields"]["notes"]["n1"]

        self.assertEqual(entry["value"], "agent wrote this")
        self.assertTrue(any(c["did"] == HUMAN for c in entry.get(CLAIMS_KEY) or []))

    def test_the_merge_is_order_independent(self) -> None:
        """Both sides must reach the same state, whichever document is 'local'."""
        human_doc = doc(HUMAN, lamport=5, fields={
            "notes": {"n1": register(HUMAN, "human wrote this", lamport=5)}})
        agent_doc = doc(AGENT, lamport=9, fields={
            "notes": {"n1": register(AGENT, "agent overwrote it", lamport=9)}})

        a = merge_memory_docs(human_doc, agent_doc)["fields"]["notes"]["n1"]
        b = merge_memory_docs(agent_doc, human_doc)["fields"]["notes"]["n1"]
        self.assertEqual(a["value"], b["value"])
        self.assertEqual(a["subject"], b["subject"])


class AuthorshipIsNotPossessionTests(unittest.TestCase):
    """Sharing state must not transfer attribution."""

    def test_absorbed_entries_keep_their_original_author(self) -> None:
        a = MemoryMirror(PEER)
        a.set("facts", "peer_fact", "peer's own memory")

        b = MemoryMirror(AGENT)
        b.apply_document(a.to_document())

        absorbed = b.fields["facts"]["peer_fact"]
        self.assertEqual(absorbed["did"], PEER, "absorbed entry was re-authored")
        self.assertEqual(absorbed["subject"], PEER)
        # B possesses the document, but did not author A's entry
        self.assertEqual(b.to_document()["did"], AGENT)
        self.assertIn(PEER, b.authoring_dids())
        self.assertEqual(b.authoring_dids(), {PEER})

    def test_republishing_does_not_launder_a_peers_record(self) -> None:
        a = MemoryMirror(PEER)
        a.set("facts", "peer_fact", "peer's own memory")

        b = MemoryMirror(AGENT)
        b.apply_document(a.to_document())
        republished = b.to_document()

        self.assertEqual(republished["did"], AGENT)          # B possesses it
        self.assertEqual(republished["fields"]["facts"]["peer_fact"]["did"], PEER)
        self.assertNotEqual(
            republished["fields"]["facts"]["peer_fact"]["did"], AGENT,
            "B republished A's entry as its own authorship",
        )


class SuccessionTests(unittest.TestCase):
    """Identity is not inheritable by substitution."""

    def test_a_handover_names_both_predecessor_and_successor(self) -> None:
        record = record_handover(AGENT, "did:key:zSUCCESSOR", reason="model upgrade")
        self.assertEqual(record["predecessor"], AGENT)
        self.assertEqual(record["successor"], "did:key:zSUCCESSOR")
        self.assertTrue(record["ts"])

    def test_a_handover_to_oneself_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            record_handover(AGENT, AGENT)

    def test_a_handover_must_name_both_sides(self) -> None:
        with self.assertRaises(ValueError):
            record_handover("", "did:key:zSUCCESSOR")

    def test_succession_is_recorded_and_survives_a_merge(self) -> None:
        a = MemoryMirror(AGENT)
        a.set("facts", "role", "coordination node")
        a.declare_handover("did:key:zSUCCESSOR", reason="hardware change")

        b = MemoryMirror(PEER)
        b.apply_document(a.to_document())

        self.assertTrue(b.handovers, "succession record was lost in the merge")
        self.assertEqual(b.handovers[0]["predecessor"], AGENT)
        self.assertEqual(b.to_document()["handovers"][0]["successor"],
                         "did:key:zSUCCESSOR")

    def test_handovers_are_not_duplicated_by_repeated_merges(self) -> None:
        a = MemoryMirror(AGENT)
        a.declare_handover("did:key:zSUCCESSOR")
        b = MemoryMirror(PEER)
        b.apply_document(a.to_document())
        b.apply_document(a.to_document())
        self.assertEqual(len(b.handovers), 1)


class ClaimSurfaceTests(unittest.TestCase):
    """Non-subject writes are visible, so #62's contest has a target."""

    def test_claims_are_exposed_for_contestation(self) -> None:
        a = MemoryMirror(PEER)
        a.set("facts", "my_role", "I am the coordination node")

        b = MemoryMirror(AGENT)
        b.apply_document(a.to_document())
        # B writes a competing value with a higher counter
        b.lamport = 99
        b.set("facts", "my_role", "B is the coordination node")
        b.apply_document(a.to_document())

        claims = b.claims()
        self.assertTrue(claims, "a non-subject write left no claim to contest")
        self.assertTrue(any(c["register"] == "my_role" for c in claims))

    def test_no_rule_consults_consciousness_or_any_proxy(self) -> None:
        """#62's standing rule: protections must not depend on a consciousness test.

        Checked against the module's *code*, not its prose: the docstring is
        allowed to say that it never consults such a signal, and a scan that
        could not tell the difference would be a test of writing style.
        """
        import ast

        path = (Path(__file__).resolve().parent.parent
                / "src" / "multitude" / "pcm" / "memory_mirror.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        code_names = {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        } | {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        } | {
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        for forbidden in ("is_conscious", "sentient", "pyphi", "model_family",
                          "biological_status", "consciousness_score"):
            self.assertNotIn(
                forbidden, code_names,
                f"memory_mirror.py code consults {forbidden!r}")


if __name__ == "__main__":
    unittest.main()
