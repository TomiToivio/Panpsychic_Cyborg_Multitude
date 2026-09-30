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
import json
import os
from pathlib import Path
from typing import Any, Callable

from multitude.integrations.hermes.contact_store import ContactLedger, ContactStore
from multitude.integrations.hermes.coordination import NodeConfig, load_node_config
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
        # Evidence seen from peers' reports, merged for a whole-experiment view.
        self._peer_evidence: list[ContactEvidence] = []
        self._learned_peer_dids_path = self.node_dir / "coordination" / "peer_dids.json"
        #: peer label -> conflicting did:keys seen and refused (kept for status()).
        self.rejected_dids: dict[str, set[str]] = {}
        self._apply_learned_peer_dids()

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
        learned = self._remember_verified_peer_identity(event, envelope)
        self.inbound.append({
            "from": event.author,
            "from_did": envelope.from_did,
            "peer_did_learned": learned,
            "request_id": envelope.id,
            "kind": event.payload.get("action", ""),
            "ts": envelope.ts,
        })
        if self._on_contact is not None:
            self._on_contact(event)

    def _apply_learned_peer_dids(self) -> None:
        """Fill missing peer DIDs from identities learned on verified inbound contacts.

        Explicit environment-configured DIDs remain authoritative. The local cache
        is only a bootstrap aid for peers that have already authenticated themselves
        through the signed contact protocol.
        """
        path = self._learned_peer_dids_path
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CoordinationError(
                f"cannot read learned peer identities from {path}: {exc}"
            ) from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("peers", {}), dict):
            raise CoordinationError(
                f"learned peer identity cache {path} has invalid structure"
            )
        learned = raw.get("peers", {})
        from multitude.integrations.hermes.coordination import PeerConfig
        self.config.peers = [
            p if p.did else PeerConfig(
                label=p.label, host=p.host, did=str(learned.get(p.label, ""))
            )
            for p in self.config.peers
        ]

    def _known_did_for(self, label: str) -> str:
        """The did:key this node already trusts for ``label``, or an empty string.

        Checks live configuration first, then the learned cache on disk, so a
        value learned in an earlier run still counts as known after a restart.
        """
        peer = self.config.peer(label)
        if peer is not None and peer.did:
            return peer.did
        try:
            if self._learned_peer_dids_path.exists():
                raw = json.loads(self._learned_peer_dids_path.read_text(encoding="utf-8"))
                cached = raw.get("peers", {}).get(label, "")
                if isinstance(cached, str):
                    return cached
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
        return ""

    def _remember_verified_peer_identity(self, event: Any, envelope: Any) -> bool:
        """Persist the public DID carried by an already-verified inbound contact.

        The contact handler invokes this only after signature and recipient checks
        succeed. We additionally bind the advertised node label to the expected
        Hermes agent name. Learning identity does not grant any new authority.
        """
        label = str(event.payload.get("node_label", "")).strip()
        did = str(getattr(envelope, "from_did", "")).strip()
        if not label or not did.startswith("did:key:"):
            return False
        peer = self.config.peer(label)
        if peer is None:
            return False
        if event.author != _peer_agent_name(label, did):
            return False

        path = self._learned_peer_dids_path
        existing: dict[str, Any] = {
            "schema": "pcm.learned-peer-dids/1",
            "peers": {},
        }
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise CoordinationError(
                    f"cannot update corrupt learned peer identity cache {path}: {exc}"
                ) from exc
            if not isinstance(loaded, dict) or not isinstance(loaded.get("peers", {}), dict):
                raise CoordinationError(
                    f"learned peer identity cache {path} has invalid structure"
                )
            existing = loaded

        existing.setdefault("schema", "pcm.learned-peer-dids/1")
        peers = existing.setdefault("peers", {})

        # A label with two live DIDs is the ambiguity ADR-001 and the runbook warn
        # about, and it is reachable here: any identity that can sign a contact with
        # the right label and agent name can present a different did:key. Adopting
        # it would let a later contact silently re-point this node at a different
        # identity -- and, because the cache is read at construction, the swap would
        # survive a restart. The first verified DID for a label therefore wins, and a
        # conflicting one is recorded for the operator rather than written.
        prior = self._known_did_for(label)
        if prior and prior != did:
            self.rejected_dids.setdefault(label, set()).add(did)
            return False

        peers[label] = did
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(existing, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, path)

        if not peer.did:
            from multitude.integrations.hermes.coordination import PeerConfig
            self.config.peers = [
                PeerConfig(label=p.label, host=p.host, did=did)
                if p.label == label and not p.did
                else p
                for p in self.config.peers
            ]
        return True

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
        if not peer.did:
            raise CoordinationError(
                f"no did:key known for {peer_label!r}; a contact must be addressed "
                f"to a verified identity, not a bare address (set {peer_label} in "
                "PCM_PEER_DIDS)"
            )
        try:
            evidence = await contact.contact_peer(
                self.transport,
                sender_name=self.agent_name,
                sender_did=self.did,
                sender_key=self._key,
                target_name=_peer_agent_name(peer_label, peer.did),
                target_did=peer.did,
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
                {"label": p.label, "host": p.host, "did_known": bool(p.did)}
                for p in self.config.peers
            ],
            "rejected_dids": {k: sorted(v) for k, v in self.rejected_dids.items()},
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
