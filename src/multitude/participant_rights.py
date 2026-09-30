# -*- coding: utf-8 -*-
"""Participant continuity and procedural-rights event domain.

This module intentionally implements procedural protections without making
claims about consciousness or moral/legal personhood. It adds no execution,
device, data, governance, or administrative capability.
"""
from __future__ import annotations

from typing import Any

EVENT_TYPES = frozenset({
    "participant_refusal",
    "participant_contest",
    "participant_claim",
    "participant_suspended",
    "participant_resumed",
    "participant_exited",
    "participant_succession",
    "participant_terminated",
})


def _state(rhizome: Any) -> dict[str, Any]:
    state = getattr(rhizome, "participant_rights", None)
    if state is None:
        state = {
            "status": {},
            "refusals": [],
            "contests": [],
            "claims": [],
            "successions": [],
            "terminations": [],
        }
        rhizome.participant_rights = state
    return state


def replay(rhizome: Any, type_: str, payload: dict[str, Any]) -> None:
    state = _state(rhizome)
    record = dict(payload.get("record") or payload)

    if type_ == "participant_refusal":
        state["refusals"].append(record)
    elif type_ == "participant_contest":
        state["contests"].append(record)
    elif type_ == "participant_claim":
        state["claims"].append(record)
    elif type_ == "participant_succession":
        state["successions"].append(record)
        predecessor = record.get("predecessor")
        successor = record.get("successor")
        if predecessor:
            state["status"][predecessor] = "succeeded"
        if successor:
            state["status"].setdefault(successor, "active")
    elif type_ == "participant_suspended":
        state["status"][record["subject"]] = "suspended"
    elif type_ == "participant_resumed":
        state["status"][record["subject"]] = "active"
    elif type_ == "participant_exited":
        state["status"][record["subject"]] = "exited"
    elif type_ == "participant_terminated":
        state["status"][record["subject"]] = "terminated"
        state["terminations"].append(record)


def status_for(rhizome: Any, subject: str) -> str:
    return _state(rhizome)["status"].get(subject, "active")


__all__ = ["EVENT_TYPES", "replay", "status_for"]
