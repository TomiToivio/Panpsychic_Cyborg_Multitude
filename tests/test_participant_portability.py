# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# The repository root contains a `multitude.py` launcher, which shadows the
# `multitude` package on the default sys.path. Every other test file in this
# repo inserts src/ first for the same reason.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.models import NodeKind, Position
from multitude.rhizome import Rhizome
from multitude.service import MultitudeService


def _participant_with_all_contribution_kinds():
    root = Path(tempfile.mkdtemp(prefix="pcm-portability-"))
    r = Rhizome.found(str(root), "R", "Charter", "Alice")
    ai = r.join("AI", NodeKind.TECHNOLOGICAL, voting=True)
    r.say("AI", "hello")
    r.remember("private thought", "mine", author="AI", visibility="private", human=False)
    proposal = r.open_proposal("P", "Body", opened_by="AI")
    r.cast_vote(proposal.id, "AI", Position.FOR)
    r.define_term("noosphere", "collective intelligence", added_by="AI")
    return r, ai, MultitudeService(r)


def test_portability_export_identifies_participant_with_stable_id():
    _r, ai, service = _participant_with_all_contribution_kinds()
    export = service.export_participant_contributions("AI")

    assert export["schema"] == "pcm.participant-contributions/1"
    assert export["participant"]["id"] == ai.id


def test_portability_export_message_has_stable_author_id():
    _r, ai, service = _participant_with_all_contribution_kinds()
    messages = service.export_participant_contributions("AI")["contributions"]["messages"]

    assert len(messages) == 1
    assert messages[0]["author_id"] == ai.id


def test_portability_export_memory_has_stable_author_id_and_preserves_private_visibility():
    _r, ai, service = _participant_with_all_contribution_kinds()
    memory = service.export_participant_contributions("AI")["contributions"]["memory"]

    assert len(memory) == 1
    assert memory[0]["author_id"] == ai.id
    assert memory[0]["visibility"] == "private"


def test_portability_export_proposal_has_stable_opener_id():
    _r, ai, service = _participant_with_all_contribution_kinds()
    proposals = service.export_participant_contributions("AI")["contributions"]["proposals"]

    assert len(proposals) == 1
    assert proposals[0]["opened_by_id"] == ai.id


def test_portability_export_vote_is_present_and_has_stable_member_id():
    _r, ai, service = _participant_with_all_contribution_kinds()
    votes = service.export_participant_contributions("AI")["contributions"]["votes"]

    assert len(votes) == 1
    assert votes[0]["vote"]["member_id"] == ai.id


def test_portability_export_lexicon_has_stable_adder_id():
    _r, ai, service = _participant_with_all_contribution_kinds()
    lexicon = service.export_participant_contributions("AI")["contributions"]["lexicon"]

    assert len(lexicon) == 1
    assert lexicon[0]["added_by_id"] == ai.id


def test_exit_with_copy_preserves_portability_export_for_former_participant():
    r, ai, service = _participant_with_all_contribution_kinds()

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
