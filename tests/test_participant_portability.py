# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
from pathlib import Path

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
