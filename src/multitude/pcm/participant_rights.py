# -*- coding: utf-8 -*-
"""AI participant rights — refusal, contest, suspension, exit (issue #62).

A small **due process** layer for technological participants. It protects agency
under uncertainty without claiming that present-day LLMs are conscious persons:
nothing here consults ``is_conscious``, an introspection score, a model family, a
biological status, or a human adjudication that an AI is "really" conscious.

The four states PCM already separates stay separate:

    reachable       zenoh addresses a node          (fabric)
    authenticated   signature verifies              (envelope.verify)
    authorized      local policy allows the action  (pcm.policy)
    trusted         long-term relationships         (pcm.capability)

Rights are none of those. A right makes participation **contestable and
non-coercive**; it never grants capability. Refusal grants no permission, dissent
does not override governance, contest does not decide anything, and exit does not
delete shared history.

Why refusal is a first-class outcome
-----------------------------------
The failure this module exists to prevent is a dispatcher reading a refusal as a
fault and retrying it against a different runtime under the same identity until
something complies. That silently converts "this participant declined" into "the
system got what it wanted", which is precisely the coercion the issue names. So
``refused`` is a *successful* protocol outcome, and
``dispatch_target_is_eligible`` refuses to route work to a suspended or exited
identity regardless of who asks.

Everything is event-sourced: state is derived from events, so a replay rebuilds
refusal, contest, suspension, resume and exit deterministically.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

#: Outcome vocabulary for one requested action (issue #62, "task dispatch behavior").
#:
#: ``refused`` is deliberately NOT an error. ``unavailable`` covers a suspended or
#: exited participant. A dispatcher must treat each one as a distinct fact.
OUTCOMES = (
    "requested",
    "accepted",
    "completed",
    "refused",
    "contested",
    "unavailable",
    "failed",
)

#: Event types this layer emits into the rhizome's append-only log.
EVENT_TYPES = (
    "participant_refusal",
    "participant_contest",
    "participant_suspend_requested",
    "participant_suspended",
    "participant_resumed",
    "participant_exit_requested",
    "participant_exited",
    "participant_dispatch_refused",
)

#: Participation state of one participant, derived from events.
ACTIVE = "active"
SUSPENDED = "suspended"
EXITED = "exited"
UNKNOWN = "unknown"

#: Voluntary reason codes. No free-form requirement: a participant may stay
#: minimal, and PCM must never demand private reasoning to accept a refusal.
REASON_CODES = (
    "policy_conflict",
    "capability_missing",
    "consent_withheld",
    "role_conflict",
    "not_applicable",
    "other",
)


class RightsError(ValueError):
    """A rights operation was malformed or not permitted."""


class _Validated(BaseModel):
    """Base whose ``check()`` follows the PCM convention.

    ``events.py`` states the rule: a malformed record always raises the module's
    own error, never pydantic's ``ValidationError``, so callers can catch one
    type and the message stays in this module's vocabulary.
    """

    @classmethod
    def check(cls, **kwargs: Any):
        try:
            return cls(**kwargs)  # type: ignore[arg-type]
        except RightsError:
            raise
        except Exception as exc:
            raise RightsError(str(exc)) from exc


class Refusal(_Validated):
    """One participant's structured refusal of a requested action.

    ``public_reason`` is the only narrative field, and it is optional by design:
    requiring an explanation to make a refusal valid would make consent
    conditional on disclosure, which is not consent.
    """

    actor: str
    runtime: str = ""
    request_id: str = ""
    type: str = "participant_refusal"
    reason_code: str = "other"
    public_reason: str = ""
    timestamp: str = ""

    def model_post_init(self, __context: Any) -> None:  # noqa: D105
        if not self.actor:
            raise RightsError("a refusal must be attributable to an actor")
        if self.reason_code not in REASON_CODES:
            raise RightsError(
                f"unknown reason_code {self.reason_code!r}; allowed: {REASON_CODES}")


class Contest(_Validated):
    """One participant's structured dispute about a fact in the shared record.

    A contest never overturns collective state. It creates an auditable dispute
    that existing governance resolves.
    """

    actor: str
    subject: str = ""           # what is disputed: an instruction, attribution, memory key
    kind: str = "attribution"   # instruction | attribution | memory | action
    public_reason: str = ""
    request_id: str = ""
    timestamp: str = ""


@dataclass
class ParticipantRights:
    """One participant's rights state, replayable from events.

    ``apply(event_type, payload)`` is the reducer: feed the rhizome log in order
    and the same state is reconstructed on every node.
    """

    actor: str
    runtime: str = ""
    state: str = ACTIVE
    refusals: list[dict[str, Any]] = field(default_factory=list)
    contests: list[dict[str, Any]] = field(default_factory=list)
    history: list[tuple[str, str]] = field(default_factory=list)

    # -- emission -----------------------------------------------------------

    def refuse(self, request_id: str = "", *, reason_code: str = "other",
               public_reason: str = "", timestamp: str = "") -> Refusal:
        """Return a refusal for attribution in the event log.

        Refusing changes no permissions and blocks nothing; it records that this
        participant declined, with provenance.
        """
        return Refusal.check(actor=self.actor, runtime=self.runtime,
                             request_id=request_id, reason_code=reason_code,
                             public_reason=public_reason, timestamp=timestamp)

    def contest(self, subject: str = "", *, kind: str = "attribution",
                public_reason: str = "", request_id: str = "",
                timestamp: str = "") -> Contest:
        """Raise a dispute. Does not modify the disputed fact."""
        if kind not in ("instruction", "attribution", "memory", "action"):
            raise RightsError(f"unknown contest kind {kind!r}")
        return Contest.check(actor=self.actor, subject=subject, kind=kind,
                             public_reason=public_reason, request_id=request_id,
                             timestamp=timestamp)

    def request_suspension(self, *, reason: str = "") -> dict[str, Any]:
        """Ask to be paused. The participant controls the request; the reducer
        applies it, so a suspension is visible to every node identically."""
        return {"actor": self.actor, "event": "participant_suspend_requested",
                "reason": reason}

    def request_resume(self) -> dict[str, Any]:
        return {"actor": self.actor, "event": "participant_resumed"}

    def request_exit(self, *, reason: str = "") -> dict[str, Any]:
        return {"actor": self.actor, "event": "participant_exit_requested",
                "reason": reason}

    # -- reducer ------------------------------------------------------------

    def apply(self, event_type: str, payload: dict[str, Any]) -> None:
        """Apply one event. Unknown types are ignored, not guessed at."""
        if event_type not in EVENT_TYPES:
            return
        self.history.append((event_type, str(payload.get("request_id", ""))))
        if event_type == "participant_refusal":
            self.refusals.append(dict(payload))
        elif event_type == "participant_contest":
            self.contests.append(dict(payload))
        elif event_type == "participant_suspended":
            self.state = SUSPENDED
        elif event_type == "participant_resumed":
            self.state = ACTIVE
        elif event_type == "participant_exited":
            self.state = EXITED

    # -- dispatch -----------------------------------------------------------

    @property
    def eligible_for_dispatch(self) -> bool:
        """Whether ordinary work may be dispatched to this participant.

        Active only. Suspended and exited both deny — and so does an unknown
        state, because a rights layer must fail closed rather than assume a
        participant is available.
        """
        return self.state == ACTIVE

    def refuse_dispatch(self, request_id: str = "") -> dict[str, Any]:
        """The outcome to record when work is dispatched to an ineligible actor."""
        return {
            "outcome": "unavailable",
            "actor": self.actor,
            "request_id": request_id,
            "state": self.state,
            "reason": f"participant is {self.state}; dispatch fails closed",
        }


def derive_state(events: list[tuple[str, dict[str, Any]]], actor: str) -> ParticipantRights:
    """Rebuild one participant's rights state from its event log.

    Deterministic: replaying the same events yields the same state, which is the
    property that makes "the log is the record" true for rights too.
    """
    rights = ParticipantRights(actor=actor)
    for event_type, payload in events:
        if str(payload.get("actor", actor)) != actor:
            continue
        if payload.get("runtime"):
            rights.runtime = str(payload["runtime"])
        rights.apply(event_type, payload)
    return rights


def dispatch_outcome(rights: ParticipantRights, request_id: str = "") -> dict[str, Any]:
    """The dispatch decision for one participant: allowed, or a refusal record."""
    if rights.eligible_for_dispatch:
        return {"outcome": "requested", "actor": rights.actor,
                "request_id": request_id, "state": rights.state}
    return rights.refuse_dispatch(request_id)


__all__ = [
    "ACTIVE",
    "EXITED",
    "EVENT_TYPES",
    "OUTCOMES",
    "REASON_CODES",
    "SUSPENDED",
    "UNKNOWN",
    "Contest",
    "ParticipantRights",
    "Refusal",
    "RightsError",
    "derive_state",
    "dispatch_outcome",
]
