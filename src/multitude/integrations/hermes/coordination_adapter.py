# -*- coding: utf-8 -*-
"""Hermes-facing coordination operations (issue #52).

The issue asks for "the smallest useful Hermes-facing operation(s)" so an agent
can inspect reachable peers, contact a named peer, acknowledge a peer, and see
which required contacts have succeeded. This module is that surface and nothing
more.

Design rules taken from the issue and ``HERMES.md``:

- **Canonical path only.** Everything here goes through ``pcm.contact`` over the
  PCM ``Transport``. There is no second Hermes message bus and no direct Zenoh
  use from Hermes code.
- **No authority is derived from contact.** Answering a contact performs no
  action on the requester's behalf and grants it nothing. ``acknowledge`` records
  and replies; it does not execute.
- **Fail closed.** An unverifiable or misaddressed contact is not answered and
  not recorded as a contact.
- **Evidence or nothing.** ``contact()`` returns evidence only for a verified,
  correlated round trip. A timeout raises; it is not reported as a successful
  contact with an empty reply.
- **No secrets.** Node configuration comes from the environment
  (``coordination.load_node_config``); no address, token or key is stored here.

The private key is read from the node's existing PCM identity
(``pcm.bootstrap.ensure_node_identity`` over the rhizome directory), so this
adapter introduces no second identity store and no new key handling.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable

from multitude.integrations.hermes.contact_store import ContactLedger, ContactStore
from multitude.integrations.hermes.coordination import NodeConfig, agent_name_for, load_node_config
from multitude.pcm import contact
from multitude.pcm.bootstrap import ensure_node_identity
from multitude.pcm.contact import ContactError, ContactEvidence, ContactMatrix
from multitude.pcm.identity import private_key_from_identity


class CoordinationError(RuntimeError):
    """The coordination operation could not be completed as requested."""


class CoordinationNode:
    """One Hermes node's coordination endpoint over a PCM transport.

    ``transport`` is any ``multitude.pcm.transport.Transport``; the Zenoh
    implementation is used in a real deployment and ``InMemoryTransport`` in
    tests, with the same protocol on both. The transport is supplied by the
    caller and started/stopped by the caller, because session lifetime is a
    deployment concern rather than a protocol one.
    """

    def __init__(
        self,
        transport: Any,
        *,
        node_dir: str | Path,
        config: NodeConfig | None = None,
        evidence_path: str | Path | None = None,
        on_contact: Callable[[Any], None] | None = None,
    ) -> None:
        self.transport = transport
        self.node_dir = Path(node_dir)
        self.config = config or load_node_config()
        identity = ensure_node_identity(str(self.node_dir))
        self.identity = identity
        self.did = identity["did"]
        self._key = private_key_from_identity(identity)
        store_path = evidence_path or (self.node_dir / "coordination" / "contacts.json")
        self.store = ContactStore(store_path)
        self._on_contact = on_contact
        self._queryable: Any = None
        # Inbound contacts this node has answered, for the status surface.
        self.inbound: list[dict[str, Any]] = []
        #: did:keys learned from verified inbound envelopes, keyed by peer label.
        self._learned_dids: dict[str, str] = {}
        #: peer label -> did:keys seen that conflict with the adopted one.
        self._did_conflicts: dict[str, set[str]] = {}
        # Evidence seen from peers' reports, merged for a whole-experiment view.
        self._peer_evidence: list[ContactEvidence] = []

    # -- identity -----------------------------------------------------------

    @property
    def agent_name(self) -> str:
        return self.config.agent_name

    @property
    def label(self) -> str:
        return self.config.label

    # -- serving (answering contacts) ---------------------------------------

    async def start_serving(self) -> None:
        """Declare the queryable that answers contact requests.

        The handler replies only to valid contacts addressed to this node; a
        malformed or misaddressed request gets silence, not an error and not an
        ack (fail closed).
        """
        handler = contact.contact_handler(
            responder_name=self.agent_name,
            responder_did=self.did,
            responder_key=self._key,
            node_label=self.label,
            on_contact=self._record_inbound,
        )
        # Declared on the did-derived selector, which is the identity the
        # contacting side verifies; the agent name is not used on the wire.
        self._queryable = await self.transport.register_queryable(
            contact.contact_selector_for_did(self.did), handler
        )

    def _record_inbound(self, event: Any, envelope: Any) -> None:
        """Record an answered contact, and learn the sender's did:key from it.

        The did:key is already on the wire: ``contact_handler`` hands over the
        signed request envelope, and ``accept_inbound_contact`` has verified that
        envelope against its own ``from`` before this callback runs. The value is
        therefore *verified identity material*, not a claim -- which is exactly
        what ``contact()`` requires in order to address a reply.

        Dropping it is what kept the three-node matrix stuck: a node could be
        contacted by a peer it could not contact back, even though the value it
        needed had just arrived. Retaining it makes one inbound contact enough to
        open the return direction, so nodes no longer deadlock waiting for each
        other to publish.
        """
        sender_did = getattr(envelope, "from_did", "") or ""
        entry = {
            "from": event.author,
            "request_id": envelope.id,
            "kind": event.payload.get("action", ""),
            "ts": envelope.ts,
        }
        # Only a did:key is usable for addressing; anything else is a malformed
        # sender identity and must not be recorded as if it were addressable.
        if sender_did.startswith("did:key:"):
            entry["from_did"] = sender_did
            self._learn_peer_did(event.author, sender_did)
        self.inbound.append(entry)
        if self._on_contact is not None:
            self._on_contact(event)

    def _learn_peer_did(self, author: str, sender_did: str) -> None:
        """Adopt a peer's verified did:key for a peer we are configured to reach.

        Two guards, because learning an identity from network input is the kind
        of thing that should not be able to widen a node's reach:

        - **Only configured peers are learned.** An unknown sender is recorded in
          ``inbound`` for inspection but does not become addressable, so a
          stranger that contacts us cannot insert itself into our peer set.
        - **The first verified did for a label wins.** A later envelope carrying
          a different did for the same label is not adopted silently; it is
          recorded as a rotation conflict, because two live dids for one node is
          the ambiguity ADR-001 and the runbook warn about.
        """
        for peer in self.config.peers:
            if agent_name_for(peer.label) != author:
                continue
            known = peer.did or self._learned_dids.get(peer.label, "")
            if known and known != sender_did:
                self._did_conflicts.setdefault(peer.label, set()).add(sender_did)
                return
            if not known:
                # Recorded separately from PeerConfig.did so status() can report
                # honestly whether a value was configured or learned on the wire.
                self._learned_dids[peer.label] = sender_did
            return

    # -- contact ------------------------------------------------------------

    async def contact(self, peer_label: str, *, note: str = "", timeout: float = 5.0) -> ContactEvidence:
        """Contact a named peer and return verified evidence of the round trip.

        Raises ``CoordinationError`` when the peer is not configured, has no
        known did, or did not acknowledge in time.
        """
        peer = self.config.peer(peer_label)
        if peer is None:
            raise CoordinationError(
                f"{peer_label!r} is not a configured peer; set PCM_PEERS "
                f"(known: {self.config.peer_labels() or 'none'})"
            )
        target_did = peer.did or self._learned_dids.get(peer_label, "")
        if not target_did:
            raise CoordinationError(
                f"no did:key known for {peer_label!r}; a contact must be addressed "
                f"to a verified identity, not a bare address (set {peer_label} in "
                "PCM_PEER_DIDS). A did:key is also learned automatically from a "
                "verified inbound contact from that peer, so one contact from them "
                "opens the return direction -- see docs/HERMES_COORDINATION.md"
            )
        try:
            evidence = await contact.contact_peer(
                self.transport,
                sender_name=self.agent_name,
                sender_did=self.did,
                sender_key=self._key,
                target_name=_peer_agent_name(peer_label, target_did),
                target_did=target_did,
                node_label=self.label,
                note=note,
                timeout=timeout,
            )
        except ContactError as exc:
            raise CoordinationError(f"contact to {peer_label!r} failed: {exc}") from exc
        self.store.append(evidence)
        return evidence

    async def contact_all(self, *, note: str = "", timeout: float = 5.0) -> dict[str, Any]:
        """Contact every configured peer. Returns a per-peer result summary.

        A failure on one peer does not abort the others: the whole point is to
        learn which directed contacts are still missing.
        """
        results: dict[str, Any] = {}
        for peer in self.config.peers:
            try:
                evidence = await self.contact(peer.label, note=note, timeout=timeout)
                results[peer.label] = {"status": "confirmed", "request_id": evidence.request_id}
            except CoordinationError as exc:
                results[peer.label] = {"status": "missing", "error": str(exc)}
        return results

    # -- acknowledging ------------------------------------------------------

    def acknowledge(self, event: Any, envelope: Any) -> dict[str, Any]:
        """Record an inbound contact as answered. Performs no other action.

        Kept as an explicit operation because the issue asks for one; the replying
        itself happens in ``start_serving``'s handler, which is where a signed
        envelope can actually be returned to the peer.
        """
        self._record_inbound(event, envelope)
        return {"acknowledged": envelope.id, "from": event.author}

    # -- inspection ---------------------------------------------------------

    def status(self) -> dict[str, Any]:
        """Current peer/contact status for the Hermes operator."""
        return {
            "node_label": self.label,
            "agent_name": self.agent_name,
            "did": self.did,
            "peers": [
                {
                    "label": p.label,
                    "host": p.host,
                    "did_known": bool(p.did or self._learned_dids.get(p.label)),
                    "did_source": (
                        "configured" if p.did
                        else "learned" if self._learned_dids.get(p.label)
                        else ""
                    ),
                }
                for p in self.config.peers
            ],
            "learned_dids": dict(self._learned_dids),
            "did_conflicts": {k: sorted(v) for k, v in self._did_conflicts.items()},
            "inbound_contacts": len(self.inbound),
            "outbound_confirmed": self.store.load() and
            [f"{e.sender_label}->{e.recipient_label}" for e in self.store.load()],
            "required_nodes": self.required_nodes(),
            "missing": [f"{a}->{b}" for a, b in self.matrix().missing_pairs()],
        }

    def required_nodes(self) -> list[str]:
        from multitude.pcm.contact import default_required_nodes
        return default_required_nodes()

    def matrix(self) -> ContactMatrix:
        """The contact matrix as this node currently knows it.

        Built from local evidence plus any peer reports merged in; it is never a
        hand-filled grid.
        """
        ledger = ContactLedger(required=self.required_nodes())
        ledger.add_store(self.store)
        for evidence in self._peer_evidence:
            ledger.add(evidence)
        return ledger.matrix

    def report(self) -> dict[str, Any]:
        """The auditable contact report, generated from evidence."""
        return self.matrix().to_report()


def _peer_agent_name(label: str, did: str) -> str:
    """The PCM entity name a peer answers on.

    Derived from the label, matching ``coordination.agent_name_for``. Kept in one
    helper so the contacting and answering sides cannot drift apart.
    """
    from multitude.integrations.hermes.coordination import agent_name_for
    return agent_name_for(label)


def run(coro: Any) -> Any:
    """Run one coordination coroutine from synchronous code (a CLI, a test)."""
    return asyncio.run(coro)


__all__ = ["CoordinationError", "CoordinationNode", "ContactLedger", "ContactStore"]
