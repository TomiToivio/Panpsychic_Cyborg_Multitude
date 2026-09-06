# -*- coding: utf-8 -*-
"""Domain reducer registry — keep Tribe._apply() small (design note).

PCM's kernel is event-sourced: ``Tribe._apply(type, payload)`` replays
one event into state. As domains accumulate (goals, economy, care,
embodiment, biosignals, assemblages...), a single monolithic reducer
becomes the kernel's biggest maintenance risk.

The registration pattern (used by goals.py already, generalized here):

    # multitude/domains/<name>.py
    EVENT_TYPES = frozenset({"economy_profile_defined", ...})

    def replay(tribe, type_, payload) -> None:
        ...

    # tribe.py binds it once:
    register_domain("economy", EVENT_TYPES, replay)

``Tribe._apply`` then routes: unknown types fall through to the core
governance reducer; registered domain types dispatch to their module's
replay function. Domains stay independent, testable, and removable —
the kernel core (events, identity, membership, memory, governance)
never grows domain branches.

This module is deliberately tiny: the registry plus the canonical
core/domain split as documentation. New domains SHOULD register here
instead of adding elif-chains to tribe.py.
"""
from __future__ import annotations

from typing import Any, Callable, Protocol


class TribeLike(Protocol):
    """The surface a domain reducer may touch (small by design)."""

    members: dict
    memory: dict
    proposals: dict
    decisions: list
    assemblages: dict


Reducer = Callable[[Any, str, dict[str, Any]], None]

# name -> {"event_types": frozenset, "replay": Reducer}
_REGISTRY: dict[str, dict[str, Any]] = {}


def register_domain(name: str, event_types: frozenset[str],
                    replay: Reducer) -> None:
    """Bind one domain's event vocabulary to its replay function."""
    if not name or not event_types or replay is None:
        raise ValueError("domain registration needs name, event_types, replay")
    for existing, entry in _REGISTRY.items():
        clash = entry["event_types"] & event_types
        if clash:
            raise ValueError(
                f"domain '{name}' event types clash with '{existing}': "
                f"{sorted(clash)}")
    _REGISTRY[name] = {"event_types": frozenset(event_types), "replay": replay}


def dispatch(type_: str) -> Reducer | None:
    """Return the registered reducer for an event type, or None."""
    for entry in _REGISTRY.values():
        if type_ in entry["event_types"]:
            return entry["replay"]
    return None


def registered_domains() -> dict[str, list[str]]:
    """Introspection: which domains own which event types."""
    return {
        name: sorted(entry["event_types"])
        for name, entry in _REGISTRY.items()
    }


# The canonical split (design contract, enforced by review):
#
#   CORE (tribe.py owns the reducer, never delegated):
#     member_joined / member_updated / member_left / membership_recorded
#     message / memory_added / memory_revised
#     proposal_opened / vote_cast / proposal_closed
#     layer_recorded
#
#   DOMAINS (register here; core never grows their branches):
#     goals/economy  -> goals.replay_goal_event  (registered at import)
#     assemblages    -> assemblage_defined / assemblage_updated
#     (future: care, rhythms, embodiment, biosignals, federation)
#
# A new domain = one module + one register_domain call. tribe.py's
# _apply stays: core branches + one dispatch() fallback.


def register_builtin_domains() -> None:
    """Bind the domains that ship with the kernel (idempotent)."""
    from multitude import goals

    if "goals" not in _REGISTRY:
        register_domain(
            "goals",
            frozenset({
                "goal_opened", "goal_closed",
                "task_opened", "task_claimed", "task_released", "task_done",
                "profit_recorded", "profit_distributed",
                "contribution_recorded", "value_flow_recorded",
                "wellbeing_recorded", "interests_declared",
            }),
            goals.replay_goal_event,
        )


__all__ = [
    "register_domain",
    "dispatch",
    "registered_domains",
    "register_builtin_domains",
    "TribeLike",
    "Reducer",
]