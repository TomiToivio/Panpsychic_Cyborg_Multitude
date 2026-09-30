from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# The repository root contains a `multitude.py`, which shadows the `multitude`
# package unless `src` is on the path first. Sibling test modules insert it at
# import time, so this file previously collected only when one of them happened
# to be imported earlier -- collection order is filesystem-dependent, so that is
# a latent break, not a guarantee.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.models import NodeKind, Position
from multitude.rhizome import Rhizome
from multitude.service import MultitudeService


def test_participant_portability_export_and_exit_copy():
    root = Path(tempfile.mkdtemp(prefix="pcm-portability-"))
    r = Rhizome.found(str(root), "R", "Charter", "Alice")
    ai = r.join("AI", NodeKind.TECHNOLOGICAL, voting=True)
    r.say("AI", "hello")
    r.remember("private thought", "mine", author="AI", visibility="private", human=False)
    p = r.open_proposal("P", "Body", opened_by="AI")
    r.cast_vote(p.id, "AI", Position.FOR)
    r.define_term("noosphere", "collective intelligence", added_by="AI")

    service = MultitudeService(r)
    export = service.export_participant_contributions("AI")
    assert export["schema"] == "pcm.participant-contributions/1"
    assert export["participant"]["id"] == ai.id
    assert export["contributions"]["messages"][0]["author_id"] == ai.id
    assert export["contributions"]["memory"][0]["author_id"] == ai.id
    assert export["contributions"]["proposals"][0]["opened_by_id"] == ai.id
    assert export["contributions"]["votes"][0]["vote"]["member_id"] == ai.id
    assert export["contributions"]["lexicon"][0]["added_by_id"] == ai.id
    assert export["contributions"]["memory"][0]["visibility"] == "private"

    before = len(r.store.replay())
    out = service.exit_participation_with_copy("AI", public_reason="leaving")
    assert out["export"]["participant"]["id"] == ai.id
    assert len(r.store.replay()) > before
    assert service.export_participant_contributions("AI")["participant"]["id"] == ai.id


def test_non_member_name_is_not_stably_attributed():
    root = Path(tempfile.mkdtemp(prefix="pcm-portability-ghost-"))
    r = Rhizome.found(str(root), "R", "Charter", "Alice")
    entry = r.remember("ghost", "text", author="Ghost Who Never Joined")
    assert entry.author_id is None


def test_each_record_type_carries_the_stable_id() -> None:
    """The prerequisite for #69: every expressive/governance record is joinable.

    These fields were added to the models in an earlier commit but not populated
    at the write sites, so the export silently returned an incomplete copy. Each
    record type is asserted individually, because leaving any one of them unwired
    degrades the copy rather than failing it.
    """
    root = Path(tempfile.mkdtemp(prefix="pcm-portability-ids-"))
    r = Rhizome.found(str(root), "R", "Charter", "Alice")
    ai = r.join("AI", NodeKind.TECHNOLOGICAL, voting=True)

    assert r.say("AI", "hello").author_id == ai.id
    assert r.remember("t", "text", author="AI").author_id == ai.id
    assert r.define_term("term", "def", added_by="AI").added_by_id == ai.id
    proposal = r.open_proposal("P", "Body", opened_by="AI")
    assert proposal.opened_by_id == ai.id
    vote = r.cast_vote(proposal.id, "AI", Position.FOR)
    assert vote.member_id == ai.id
    # `member` is already the stable id for a vote; keep it that way.
    assert vote.member == ai.id


def test_the_copy_is_visibility_aware_and_self_directed_only() -> None:
    """A copy is the owner's own record: it includes its private entries and
    excludes everyone else's, and says which policy it applied."""
    root = Path(tempfile.mkdtemp(prefix="pcm-portability-vis-"))
    r = Rhizome.found(str(root), "R", "Charter", "Alice")
    r.join("AI", NodeKind.TECHNOLOGICAL, voting=True)
    r.remember("mine-private", "x", author="AI", visibility="private", human=False)
    r.remember("mine-restricted", "x", author="AI", visibility="restricted")
    r.remember("mine-shared", "x", author="AI", visibility="shared")
    r.remember("alice-private", "x", author="Alice", visibility="private")

    export = MultitudeService(r).export_participant_contributions("AI")
    titles = {m["title"] for m in export["contributions"]["memory"]}
    assert titles == {"mine-private", "mine-restricted", "mine-shared"}
    assert "alice-private" not in titles, "another member's private entry leaked"
    assert "visibility_policy" in export


def test_a_departed_member_can_still_be_queried_and_take_its_copy() -> None:
    """Leaving must not make the leaver unreachable (#62/#69).

    `participant_status` and the export both have to resolve former members:
    the exit is precisely what the departing participant wants to confirm, and
    the copy has to remain obtainable after the fact.
    """
    root = Path(tempfile.mkdtemp(prefix="pcm-portability-exit-"))
    r = Rhizome.found(str(root), "R", "Charter", "Alice")
    ai = r.join("AI", NodeKind.TECHNOLOGICAL, voting=True)
    r.say("AI", "hi")
    r.remember("note", "text", author="AI")
    service = MultitudeService(r)

    memory_before = len(r.memory)
    messages_before = len(r.messages)
    out = service.exit_participation_with_copy("AI", public_reason="leaving")

    assert service.participant_status("AI") == "exited"
    assert out["export"]["participant"]["id"] == ai.id
    after = service.export_participant_contributions("AI")
    assert after["participant"]["id"] == ai.id
    assert after["contributions"] == out["export"]["contributions"]
    # The collective's history is not mutated or trimmed by taking a copy.
    assert len(r.memory) == memory_before
    assert len(r.messages) == messages_before
    assert any(m.author == "AI" for m in r.memory.values())
    assert any(m.author_id == ai.id for m in r.messages)
