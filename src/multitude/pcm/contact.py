# -*- coding: utf-8 -*-
"""PCM coordination — evidence-bearing contact between Hermes nodes.

Issue #52 asks three Hermes nodes (Laskin, lh6-725-37563, NooPunk) to contact each
other through PCM over Zenoh and to prove it with a six-entry directed contact
matrix. This module is the protocol half of that: what a contact *is*, how an
acknowledgement is correlated to it, and how the evidence becomes a matrix.

It rides the canonical pieces and invents nothing:

- transport: ``multitude.pcm.transport.Transport`` (``ZenohTransport`` in a real
  deployment, ``InMemoryTransport`` in tests) — the documented request/response
  pattern from ``docs/NETWORKING_STACK.md`` §9;
- envelope: ``pcm.envelope.Envelope`` — every contact and every ack is a signed,
  verifiable envelope;
- event: ``pcm.events.PcmEvent`` with the existing ``pcm.agent.request`` /
  ``pcm.agent.response`` types, so no new vocabulary is added;
- keys: ``pcm/query/agent/<name>`` — the namespace's request/response endpoint.

Why discovery is not proof
--------------------------
A liveliness token or a wildcard scan tells you a node exists. It does not tell
you that node received anything, agreed it was addressed, or answered. Issue #52
is explicit that "mere Zenoh discovery/liveliness" must not be treated as
contact. So a contact here is a *round trip*:

    A --pcm.agent.request (signed)--> B
    A <--pcm.agent.response (signed, references the request)-- B

The ack is only evidence when all of these hold, and ``verify_contact`` checks
every one of them rather than assuming any:

1. both envelopes verify against the did:key embedded in their ``from``;
2. the ack's ``from`` is the node we contacted (it is *that* node answering);
3. the ack's ``to`` is us (it was addressed to us, not broadcast);
4. the ack references the exact request it answers (correlation, so an ack for
   somebody else's contact is not counted as ours);
5. both carry the same contact kind.

Safety: this module sends and verifies small JSON messages. It cannot execute
anything on a peer, and an ack grants no authority over the sender — reachability
is not authorization (``pcm.policy``). What to do on receiving a contact is the
peer's decision, inside the peer's own permissions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from multitude.pcm.envelope import Envelope, EnvelopeError
from multitude.pcm.events import EventError, PcmEvent
from multitude.pcm.namespace import validate_key

# The contact kind, carried in the request event payload. A string rather than a
# new event *type*: the existing pcm.agent.request/response types already mean
# exactly this exchange, and issue #52 asks not to extend the vocabulary unless
# the current model genuinely cannot represent the interaction.
CONTACT_KIND = "coordination.hello"

# The documented request/response endpoint for one agent name.
QUERY_DOMAIN = "query"


class ContactError(ValueError):
    """A contact or acknowledgement is malformed, unverifiable, or not ours."""


def contact_selector(name: str) -> str:
    """The PCM key a node answers contact requests on, from its agent name.

    ``agent:hermes-noopunk`` -> ``pcm/query/agent/hermes-noopunk``.

    Prefer :func:`contact_selector_for_did` on the wire: it is derived from the
    identity that is already verified, so the contacting and answering sides
    cannot disagree about the name.
    """
    entity = name.split(":", 1)[-1]
    return validate_key(f"pcm/{QUERY_DOMAIN}/agent/{entity}")


def contact_selector_for_did(did: str) -> str:
    """The PCM key a node answers contact requests on, from its did:key.

    The last 16 characters of the base58 did body are unique in practice for a
    three-node experiment and are a valid namespace segment, so the selector is
    derived from the one identity both sides already agree on rather than from a
    configured name that could drift.
    """
    if not did.startswith("did:key:"):
        raise ContactError(f"not a did:key: {did!r}")
    short = did.rsplit(":", 1)[-1][-16:]
    if not short:
        raise ContactError(f"did has no body: {did!r}")
    return validate_key(f"pcm/{QUERY_DOMAIN}/agent/{short}")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Building the two envelopes
# ---------------------------------------------------------------------------


def build_contact_request(
    *,
    sender_name: str,
    sender_did: str,
    recipient_name: str,
    recipient_did: str,
    node_label: str,
    note: str = "",
    interface: str = "zenoh",
) -> Envelope:
    """Build (but do not sign) a contact request envelope A -> B."""
    selector = contact_selector(recipient_name)
    event = PcmEvent(
        type="pcm.agent.request",
        author=sender_name,
        subject=selector,
        payload={
            "action": CONTACT_KIND,
            "target": recipient_name,
            "node_label": node_label,
            "note": note,
            "protocol": "pcm-coordination/1",
        },
        metadata={"recipient_did": recipient_did},
        timestamp=_now(),
    )
    return Envelope.create(
        "say",
        sender_did,
        recipient_did,
        event.to_envelope_content(),
        interface=interface,
        actor_kind="ai",
    )


def build_contact_ack(
    *,
    request: Envelope,
    responder_name: str,
    responder_did: str,
    node_label: str,
    note: str = "",
    interface: str = "zenoh",
) -> Envelope:
    """Build (but do not sign) the acknowledgement answering ``request``.

    The ack is addressed back to the request's sender and references the request
    envelope id, which is what makes it attributable and correlatable rather than
    a free-floating "hello".
    """
    request_event = _event_of(request)
    return Envelope.create(
        "say",
        responder_did,
        request.from_did,
        PcmEvent(
            type="pcm.agent.response",
            author=responder_name,
            subject=contact_selector(responder_name),
            payload={
                "action": CONTACT_KIND,
                "node_label": node_label,
                "note": note,
                "protocol": "pcm-coordination/1",
                "acknowledges": request.id,
            },
            references=[{"kind": "pcm.agent.request", "id": request.id,
                         "author": request_event.author}],
            metadata={"request_id": request.id},
            timestamp=_now(),
        ).to_envelope_content(),
        interface=interface,
        actor_kind="ai",
    )


def _event_of(envelope: Envelope) -> PcmEvent:
    """Extract and validate the PCM event carried in an envelope."""
    payload = envelope.content.get("event")
    if not isinstance(payload, dict):
        raise ContactError("envelope carries no PCM event")
    try:
        return PcmEvent.model_validate(payload)
    except Exception as exc:  # pydantic wraps our EventError
        raise ContactError(f"malformed PCM event: {exc}") from exc


# ---------------------------------------------------------------------------
# Verification — what counts as evidence
# ---------------------------------------------------------------------------


class ContactEvidence(BaseModel):
    """One proven directed contact. This is what the report is built from."""

    sender: str                       # pcm id, e.g. agent:hermes-noopunk
    sender_label: str                 # node label, e.g. NooPunk
    sender_did: str
    recipient: str
    recipient_label: str
    recipient_did: str
    request_id: str
    ack_id: str
    contact_kind: str = CONTACT_KIND
    protocol: str = "pcm-coordination/1"
    request_ts: str = ""
    ack_ts: str = ""
    note: str = ""
    verified: bool = True


def verify_contact(
    request: dict[str, Any] | Envelope,
    ack: dict[str, Any] | Envelope,
    *,
    verified_here: bool = True,
) -> ContactEvidence:
    """Prove that ``ack`` is a genuine reply to ``request``, or raise.

    Every check the module docstring lists is enforced. ``verified_here=False``
    is available for a caller that has *already* run ``Envelope.verify()`` at the
    transport edge (the Zenoh transport does) and does not want to verify twice;
    correlation and direction are still checked either way.
    """
    req_env = request if isinstance(request, Envelope) else _validate(request)
    ack_env = ack if isinstance(ack, Envelope) else _validate(ack)
    if verified_here:
        _verify_signature(req_env)
        _verify_signature(ack_env)

    req_event = _event_of(req_env)
    ack_event = _event_of(ack_env)

    if req_event.type != "pcm.agent.request":
        raise ContactError(f"request is {req_event.type!r}, not pcm.agent.request")
    if req_event.payload.get("action") != CONTACT_KIND:
        raise ContactError(f"not a {CONTACT_KIND} request")
    if ack_event.type != "pcm.agent.response":
        raise ContactError(f"ack is {ack_event.type!r}, not pcm.agent.response")

    # direction: the ack must come from the node we contacted...
    if ack_env.from_did != req_env.to_did:
        raise ContactError(
            "ack was not sent by the contacted node "
            f"({ack_env.from_did} != {req_env.to_did})"
        )
    # ...and must be addressed to us.
    if ack_env.to_did != req_env.from_did:
        raise ContactError(
            "ack was not addressed to the requesting node "
            f"({ack_env.to_did} != {req_env.from_did})"
        )
    # correlation: an ack for a different contact is not evidence for this one.
    acknowledged = ack_event.payload.get("acknowledges") or ack_event.metadata.get("request_id")
    if acknowledged != req_env.id:
        raise ContactError(
            f"ack does not reference this request ({acknowledged!r} != {req_env.id!r})"
        )
    if ack_event.payload.get("action") != CONTACT_KIND:
        raise ContactError("ack is for a different contact kind")

    return ContactEvidence(
        sender=req_event.author,
        sender_label=str(req_event.payload.get("node_label", "")),
        sender_did=req_env.from_did,
        recipient=ack_event.author,
        recipient_label=str(ack_event.payload.get("node_label", "")),
        recipient_did=ack_env.from_did,
        request_id=req_env.id,
        ack_id=ack_env.id,
        request_ts=req_env.ts,
        ack_ts=ack_env.ts,
        note=str(ack_event.payload.get("note", "")),
    )


def _validate(data: dict[str, Any]) -> Envelope:
    try:
        return Envelope.model_validate(data)
    except Exception as exc:
        raise ContactError(f"malformed envelope: {exc}") from exc


def _verify_signature(envelope: Envelope) -> None:
    try:
        envelope.verify()
    except EnvelopeError as exc:
        raise ContactError(f"signature does not verify: {exc}") from exc


def accept_inbound_contact(
    request: dict[str, Any] | Envelope,
    *,
    expected_name: str,
) -> PcmEvent:
    """Validate a contact request that arrived for us, or raise.

    Used by the answering side: a request addressed to somebody else, or carrying
    a different action, is not ours to answer. Returns the request's event so the
    responder knows what to acknowledge.
    """
    req_env = request if isinstance(request, Envelope) else _validate(request)
    _verify_signature(req_env)
    event = _event_of(req_env)
    if event.type != "pcm.agent.request":
        raise ContactError(f"inbound message is {event.type!r}, not a request")
    if event.payload.get("action") != CONTACT_KIND:
        raise ContactError(f"inbound message is not a {CONTACT_KIND} contact")
    if event.payload.get("target") != expected_name:
        raise ContactError(
            f"contact was addressed to {event.payload.get('target')!r}, not {expected_name!r}"
        )
    return event


# ---------------------------------------------------------------------------
# The contact matrix
# ---------------------------------------------------------------------------


class ContactMatrix(BaseModel):
    """Which directed contacts among the required nodes are proven.

    The matrix is built *only* from verified evidence — ``record()`` refuses an
    unverified or off-list contact. Nothing here can be set by hand at report
    time, because the report reads the records, not a pre-filled grid.
    """

    required: list[str]
    required_dids: dict[str, str] = Field(default_factory=dict)
    records: list[ContactEvidence] = Field(default_factory=list)

    def record(self, evidence: ContactEvidence) -> bool:
        """Add one proven contact. Returns False when it does not count."""
        if not evidence.verified:
            return False
        if evidence.sender_label not in self.required:
            return False
        if evidence.recipient_label not in self.required:
            return False
        if evidence.sender_label == evidence.recipient_label:
            return False
        # de-duplicate: re-contacting a peer does not add a second row
        for existing in self.records:
            if (existing.sender_label == evidence.sender_label
                    and existing.recipient_label == evidence.recipient_label):
                return False
        self.records.append(evidence)
        return True

    def confirmed_pairs(self) -> list[tuple[str, str]]:
        return sorted((r.sender_label, r.recipient_label) for r in self.records)

    def required_pairs(self) -> list[tuple[str, str]]:
        """Every directed pair the experiment needs: n*(n-1) of them."""
        return [(a, b) for a in self.required for b in self.required if a != b]

    def missing_pairs(self) -> list[tuple[str, str]]:
        done = set(self.confirmed_pairs())
        return [pair for pair in self.required_pairs() if pair not in done]

    @property
    def complete(self) -> bool:
        return not self.missing_pairs()

    def status(self, sender: str, recipient: str) -> str:
        return "confirmed" if (sender, recipient) in set(self.confirmed_pairs()) else "missing"

    def to_report(self) -> dict[str, Any]:
        """The auditable artifact: matrix + completeness + the evidence behind it."""
        matrix = {
            sender: {
                recipient: "confirmed" if (sender, recipient) in set(self.confirmed_pairs())
                else "missing"
                for recipient in self.required
                if recipient != sender
            }
            for sender in self.required
        }
        return {
            "kind": "pcm.contact_report/1",
            "generated_at": _now(),
            "required_nodes": list(self.required),
            "complete": self.complete,
            "confirmed_count": len(self.records),
            "required_count": len(self.required_pairs()),
            "missing": [{"from": a, "to": b} for a, b in self.missing_pairs()],
            "matrix": matrix,
            "evidence": [r.model_dump() for r in self.records],
        }


def default_required_nodes() -> list[str]:
    """The three nodes issue #52 names, in a stable order."""
    return ["Laskin", "lh6-725-37563", "NooPunk"]


# ---------------------------------------------------------------------------
# Transport glue (async)
# ---------------------------------------------------------------------------


async def contact_peer(
    transport: Any,
    *,
    sender_name: str,
    sender_did: str,
    sender_key: Any,
    target_name: str,
    target_did: str,
    node_label: str,
    note: str = "",
    timeout: float = 5.0,
) -> ContactEvidence:
    """Contact one peer and return the proven evidence, or raise ContactError.

    Sends to the peer's documented query selector and requires a correctly
    correlated ack. No ack inside the timeout is a failed contact, not a success
    with an empty reply — a request that nobody answered has not been delivered.
    """
    request = build_contact_request(
        sender_name=sender_name,
        sender_did=sender_did,
        recipient_name=target_name,
        recipient_did=target_did,
        node_label=node_label,
        note=note,
    )
    request.sign(sender_key, sender_did)
    replies = await transport.request(
        contact_selector_for_did(target_did),
        request.model_dump(by_alias=True),
        timeout=timeout,
    )
    problems: list[str] = []
    for reply in replies:
        try:
            return verify_contact(request.model_dump(by_alias=True), reply)
        except ContactError as exc:
            problems.append(str(exc))
    if problems:
        raise ContactError("no usable acknowledgement: " + "; ".join(problems))
    raise ContactError(
        f"no acknowledgement from {target_name!r} within {timeout}s "
        "(a request nobody answered is not a contact)"
    )


def contact_handler(
    *,
    responder_name: str,
    responder_did: str,
    responder_key: Any,
    node_label: str,
    on_contact: Any = None,
) -> Any:
    """Build the queryable handler that answers contact requests with a signed ack.

    The handler answers *only* valid, correctly addressed contacts, and records
    what it answered via the optional ``on_contact(event)`` callback. It never
    takes action on behalf of the requester — an ack is not authority.
    """
    def handler(payload: Any, topic: str) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        try:
            request = _validate(payload)
            accept_inbound_contact(request, expected_name=responder_name)
        except ContactError:
            return None  # unverifiable or misaddressed contacts get silence
        ack = build_contact_ack(
            request=request,
            responder_name=responder_name,
            responder_did=responder_did,
            node_label=node_label,
        )
        ack.sign(responder_key, responder_did)
        if on_contact is not None:
            try:
                on_contact(_event_of(request), request)
            except Exception:
                pass
        return ack.model_dump(by_alias=True)

    return handler


__all__ = [
    "CONTACT_KIND",
    "ContactError",
    "ContactEvidence",
    "ContactMatrix",
    "accept_inbound_contact",
    "build_contact_ack",
    "build_contact_request",
    "contact_handler",
    "contact_peer",
    "contact_selector",
    "contact_selector_for_did",
    "default_required_nodes",
    "verify_contact",
]
