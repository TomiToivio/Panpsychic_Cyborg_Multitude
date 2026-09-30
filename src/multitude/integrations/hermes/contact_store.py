# -*- coding: utf-8 -*-
"""Contact evidence store — where proven coordination contacts are kept.

The issue demands a machine-readable contact report whose entries come from
actual PCM messages and acknowledgements, "not a manually edited declaration".
So the report is generated from a store that only ever receives
``ContactEvidence`` produced by ``pcm.contact.verify_contact``: there is no path
that writes "confirmed" into the report directly.

Two backends, both local files (nothing here touches the network):

- ``ContactStore``   — one JSON file per node, a list of verified evidence;
- ``ContactLedger``  — the same, merged across nodes for a whole-experiment view.

The ledger merge is deliberately conservative. Two nodes in the same experiment
may each hold the *same* directed contact from opposite ends (A recorded "A->B",
B recorded "A contacted me"). Those are one contact, not two, so merge
de-duplicates on the (sender_label, recipient_label) pair rather than counting
records — otherwise a two-node experiment would appear to have double evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from multitude.pcm.contact import (
    ContactEvidence,
    ContactMatrix,
    default_required_nodes,
)


class ContactStore:
    """One node's record of the contacts it has proven, as a JSON file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> list[ContactEvidence]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            # A corrupt evidence file must not silently read as "no contacts":
            # that would turn a real error into a missing contact, which is the
            # kind of quiet failure the issue warns about.
            raise ValueError(f"contact store {self.path} is not valid JSON: {exc}") from exc
        return [ContactEvidence.model_validate(item) for item in raw]

    def append(self, evidence: ContactEvidence) -> bool:
        """Store one proven contact. Returns False if it was already recorded."""
        records = self.load()
        for existing in records:
            if (existing.sender_label == evidence.sender_label
                    and existing.recipient_label == evidence.recipient_label):
                return False
        records.append(evidence)
        self._write(records)
        return True

    def contact_events(self) -> list[dict[str, Any]]:
        """The contacts this node *received* (the other half of each round trip)."""
        events: list[dict[str, Any]] = []
        if not self.path.exists():
            return events
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        for item in raw:
            inbound = item.get("inbound")
            if inbound:
                events.append(inbound)
        return events

    def _write(self, records: list[ContactEvidence]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [r.model_dump() for r in records]
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")


class ContactLedger:
    """A whole-experiment view: evidence merged from several nodes' stores."""

    def __init__(self, required: Iterable[str] | None = None) -> None:
        nodes = list(required) if required is not None else default_required_nodes()
        self.matrix = ContactMatrix(required=nodes)

    def add(self, evidence: ContactEvidence) -> bool:
        return self.matrix.record(evidence)

    def add_store(self, store: ContactStore) -> int:
        """Merge one node's store. Returns how many new contacts it contributed."""
        added = 0
        for evidence in store.load():
            if self.add(evidence):
                added += 1
        return added

    def add_stores(self, stores: Iterable[ContactStore]) -> int:
        return sum(self.add_store(store) for store in stores)

    def report(self) -> dict[str, Any]:
        return self.matrix.to_report()

    @property
    def complete(self) -> bool:
        return self.matrix.complete


__all__ = ["ContactLedger", "ContactStore"]
