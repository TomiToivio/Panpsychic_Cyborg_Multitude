# -*- coding: utf-8 -*-
"""TribeStore: append-only event log plus tribe config, one directory per tribe.

Local-first by design. The event log is the tribe's collective memory:
nothing is ever deleted or rewritten, corrections are new events, and any
node can replay the full history. tribe.json only carries discovery
metadata (name, slug, charter, founded timestamp); everything else lives
in events.jsonl.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from typing import Any

from multitude.models import Event, PrivateNote, new_id, now_iso

EVENTS_FILE = "events.jsonl"
CONFIG_FILE = "tribe.json"
PRIVATE_NOTES_FILE = "private_notes.jsonl"


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "tribe"


class TribeStore:
    def __init__(self, path: str) -> None:
        self.path = path
        os.makedirs(path, exist_ok=True)
        self.events_path = os.path.join(path, EVENTS_FILE)
        self.config_path = os.path.join(path, CONFIG_FILE)
        self.private_notes_path = os.path.join(path, PRIVATE_NOTES_FILE)

    @classmethod
    def create(cls, root: str, name: str, charter: str = "") -> "TribeStore":
        """Create a fresh tribe directory under root (slug deduplicated)."""
        tribe_dir = os.path.join(root, slugify(name))
        base, n = tribe_dir, 2
        while os.path.exists(tribe_dir):
            tribe_dir = f"{base}-{n}"
            n += 1
        store = cls(tribe_dir)
        store.write_config(
            {
                "name": name,
                "slug": os.path.basename(tribe_dir),
                "charter": charter,
                "founded_ts": now_iso(),
            }
        )
        return store

    def write_config(self, config: dict[str, Any]) -> None:
        """Atomic write so a crash never leaves a half-written tribe.json."""
        fd, tmp = tempfile.mkstemp(dir=self.path, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(config, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self.config_path)

    def read_config(self) -> dict[str, Any]:
        if not os.path.exists(self.config_path):
            return {}
        with open(self.config_path, encoding="utf-8") as fh:
            return json.load(fh)

    def append(self, type_: str, actor: str, payload: dict[str, Any]) -> Event:
        event = Event(
            id=new_id("ev"), type=type_, ts=now_iso(), actor=actor, payload=payload
        )
        with open(self.events_path, "a", encoding="utf-8") as fh:
            fh.write(event.model_dump_json() + "\n")
        return event

    def replay(self) -> list[Event]:
        events: list[Event] = []
        seen_ids: set[str] = set()
        if not os.path.exists(self.events_path):
            return events
        with open(self.events_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = Event.model_validate_json(line)
                except Exception:
                    # Merge safety: malformed tail lines or partial writes are ignored
                    # instead of crashing the entire replay. The log remains append-only.
                    continue
                if event.id in seen_ids:
                    continue
                seen_ids.add(event.id)
                events.append(event)
        return events

    def append_private_note(self, note: PrivateNote) -> PrivateNote:
        with open(self.private_notes_path, "a", encoding="utf-8") as fh:
            fh.write(note.model_dump_json() + "\n")
        return note

    def replay_private_notes(self) -> list[PrivateNote]:
        notes: list[PrivateNote] = []
        if not os.path.exists(self.private_notes_path):
            return notes
        with open(self.private_notes_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                notes.append(PrivateNote.model_validate_json(line))
        return notes
