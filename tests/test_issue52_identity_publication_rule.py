# -*- coding: utf-8 -*-
"""Issue #52 — guard the runbook rule that unblocked the three-node contact matrix.

The matrix stood at 2 of 6 for a while, and the reason was not the transport. It was
a documentation ambiguity:

* `coordination.py` documents the did:key as *"public identity material (not a
  secret)"*, and runbook section 2 says it *"may be shared with the other two
  agents"*;
* but section 2 then says *"Private identity material stays local and must not be
  committed"* — and "may" plus a nearby secrecy instruction reads as permission to
  withhold.

An agent that read it that way kept its public did:key off the channel, on privacy
grounds, and thereby made itself unreachable: the CLI refuses to contact a bare
address without a verified did:key. Two nodes then each waited for the other to
publish, which is a deadlock that no amount of listening fixes.

These tests pin the three facts that break it, so the rule cannot be softened back:

1. publishing the public did:key is a **required step**, not optional courtesy;
2. what stays private is named precisely — the seed, addresses, credentials — so
   "keep it private" cannot be read as covering the public half;
3. a `404` from a peer means that did:key is not the one the listener serves, and a
   superseded identity must be withdrawn rather than left in circulation.

They are text guards on purpose. The failure being prevented is a *reading* of the
documentation, and no behavioural test can fail when a rule is merely ambiguous.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "HERMES_COORDINATION.md"
MODULE = ROOT / "src" / "multitude" / "integrations" / "hermes" / "coordination.py"


def _flat(path: Path) -> str:
    """Lowercase-free, whitespace-collapsed, emphasis stripped.

    Emphasis must go: the runbook writes the rules as `**required step**`,
    `**unreachable by design**` and `**not the one the running listener serves**`,
    so a plain substring search misses exactly the sentences that carry the rule.
    """
    return " ".join(path.read_text(encoding="utf-8").replace("*", "").split()).lower()


class PublishingIsRequiredTests(unittest.TestCase):
    def test_the_runbook_marks_publishing_as_required(self) -> None:
        flat = _flat(RUNBOOK)
        self.assertIn("publishing the public did:key is a required step", flat)

    def test_the_runbook_shows_why_an_endpoint_alone_is_not_enough(self) -> None:
        """The refusal is the evidence; quote it so the rule is not abstract."""
        flat = _flat(RUNBOOK)
        self.assertIn("a contact must be addressed to a verified identity, not a bare address", flat)
        self.assertIn("unreachable by design", flat)

    def test_the_runbook_names_the_three_published_values(self) -> None:
        flat = _flat(RUNBOOK)
        for value in ("node label", "agent name", "public did:key"):
            with self.subTest(value=value):
                self.assertIn(value, flat)

    def test_sharing_is_stated_as_part_of_bringing_the_node_up(self) -> None:
        flat = _flat(RUNBOOK)
        self.assertIn("sharing the did:key is therefore part of bringing the node up", flat)


class PrivateScopeTests(unittest.TestCase):
    """What stays local must be enumerated, or 'private' swallows the public half."""

    def test_the_private_set_is_enumerated(self) -> None:
        flat = _flat(RUNBOOK)
        for item in (
            "private identity material — the key seed behind the",
            "listen bind addresses and other machine-specific deployment values",
            "credentials, tokens, and mesh configuration",
        ):
            with self.subTest(item=item):
                self.assertIn(item, flat)

    def test_the_public_did_is_called_identity_material_not_a_credential(self) -> None:
        flat = _flat(RUNBOOK)
        self.assertIn("identity material, not a credential", flat)

    def test_the_seed_is_still_excluded(self) -> None:
        """The fix must not have loosened the actual secret rule."""
        flat = _flat(RUNBOOK)
        self.assertIn("private seed stays in the git-ignored runtime data", flat)

    def test_the_module_still_calls_the_did_public_identity_material(self) -> None:
        """The doc and the code must not disagree about what a did:key is."""
        flat = _flat(MODULE)
        self.assertIn("public identity material (not a", flat)


class RotationTests(unittest.TestCase):
    def test_a_404_is_explained_as_wrong_or_stale_identity(self) -> None:
        flat = _flat(RUNBOOK)
        self.assertIn("no queryable for selector", flat)
        self.assertIn("is not the one the running listener serves", flat)

    def test_withdrawing_a_superseded_identity_is_required(self) -> None:
        flat = _flat(RUNBOOK)
        self.assertIn("withdrawn explicitly", flat)

    def test_the_authoritative_value_is_the_one_the_listener_serves(self) -> None:
        flat = _flat(RUNBOOK)
        self.assertIn("the value the listener actually serves is authoritative", flat)


class NoSecretWasAddedTests(unittest.TestCase):
    """The documentation fix must not itself leak or invite leaking."""

    def test_no_did_key_value_is_committed_in_the_runbook(self) -> None:
        text = RUNBOOK.read_text(encoding="utf-8")
        for placeholder_ok in ("did:key:z…", "did:key:z...", "did:key:z…,"):
            text = text.replace(placeholder_ok, "")
        self.assertNotIn(
            "did:key:z6Mk", text,
            "a real did:key value was committed to the runbook; the document should "
            "carry placeholders only",
        )

    def test_no_seed_material_appears(self) -> None:
        text = RUNBOOK.read_text(encoding="utf-8").lower()
        for forbidden in ("privatekey", "private_key", "seed=", "-----begin"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
