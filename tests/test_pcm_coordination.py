# -*- coding: utf-8 -*-
"""Issue #52 — the PCM coordination protocol and its contact evidence.

These tests cover protocol *semantics*, not the live three-machine experiment:
they run entirely in-process over ``InMemoryTransport`` so normal CI needs no
network, no router and no peer machines. The real three-node procedure is an
explicit runbook (``docs/HERMES_COORDINATION.md``), not a CI job.

The distinction the issue insists on is what most of this file is about: a
contact is a verified, correlated round trip, and *discovery is not contact*.
Several tests exist purely to prove that a wrong or weak acknowledgement is
rejected rather than counted.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Same bootstrap the other PCM tests use: the repo root holds a ``multitude.py``
# launcher that would otherwise shadow the ``multitude`` package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.integrations.hermes.contact_store import ContactLedger, ContactStore
from multitude.integrations.hermes.coordination import (
    NodeConfig,
    PeerConfig,
    agent_name_for,
    load_node_config,
    peers_from_env,
)
from multitude.integrations.hermes.coordination_adapter import (
    CoordinationError,
    CoordinationNode,
)
from multitude.pcm import contact as pc
from multitude.pcm.contact import (
    ContactError,
    ContactMatrix,
    build_contact_ack,
    build_contact_request,
    contact_selector_for_did,
    verify_contact,
)
from multitude.pcm.envelope import Envelope
from multitude.pcm.identity import generate_identity, private_key_from_identity
from multitude.pcm.transport import InMemoryTransport


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def make_identity(tmp: Path, name: str):
    directory = tmp / name
    directory.mkdir(parents=True, exist_ok=True)
    identity = generate_identity(str(directory))
    return identity, private_key_from_identity(identity), directory


class Node:
    """One in-process coordination node with its own identity and store.

    ``fabric`` is a shared pub/sub fabric (the existing ``InMemoryTransport``
    used as a hub between nodes). Each node has its own transport, so an inbound
    request reaches the answering node's registered queryable and nothing else —
    a node can only receive a contact addressed to its own selector.
    """

    def __init__(self, tmp: Path, label: str, peers: list[str],
                 fabric: "Fabric | None" = None):
        self.identity, self.key, self.dir = make_identity(tmp, label)
        self.did = self.identity["did"]
        self.label = label
        self.transport = (fabric or Fabric()).transport_for(agent_name_for(label))
        self.node = CoordinationNode(
            self.transport,
            node_dir=self.dir,
            config=NodeConfig(
                label=label,
                agent_name=agent_name_for(label),
                peers=[PeerConfig(label=p, host="127.0.0.1") for p in peers],
            ),
        )

    async def start(self, *, serve: bool = True):
        """Join the fabric. ``serve=False`` is a node that is present but not
        answering — reachable, yet not contactable, which is the distinction the
        issue insists on."""
        await self.transport.start()
        if serve:
            await self.node.start_serving()
        return self


class Fabric:
    """A shared in-process PCM fabric: pub/sub plus query routing between nodes."""

    def __init__(self) -> None:
        self._subs: list[tuple[Any, Any]] = []       # (regex, handler)
        self._queryables: dict[str, Any] = {}        # key -> handler

    def transport_for(self, pcm_id: str):
        fabric = self

        class _NodeTransport(InMemoryTransport):
            async def publish(self, topic: str, event: dict) -> None:
                for regex, handler in list(fabric._subs):
                    if regex.match(topic):
                        result = handler(event, topic)
                        if asyncio.iscoroutine(result):
                            await result

            async def subscribe(self, pattern: str, handler):
                from multitude.pcm.transport import _wildcard_to_regex
                self._subs.append((_wildcard_to_regex(pattern), handler))
                return ("fabric-sub", pattern)

            async def register_queryable(self, selector: str, handler):
                fabric._queryables[selector] = handler
                return ("fabric-q", selector)

            async def request(self, selector: str, payload=None, timeout: float = 5.0):
                from multitude.pcm.transport import _wildcard_to_regex
                regex = _wildcard_to_regex(selector)
                replies = []
                for key, handler in list(fabric._queryables.items()):
                    if regex.match(key):
                        result = handler(payload, key)
                        if asyncio.iscoroutine(result):
                            result = await result
                        if result is not None:
                            replies.append(result)
                return replies

        return _NodeTransport({"pcm_id": pcm_id})


def wire_peer_dids(*nodes: Node) -> None:
    """Give each node the others' public dids, as the environment mapping does."""
    for node in nodes:
        node.node.config.peers = [
            PeerConfig(label=p.label, host=p.host, did=_did_of(p.label, nodes))
            for p in node.node.config.peers
        ]


def _did_of(label: str, nodes) -> str:
    for node in nodes:
        if node.label == label:
            return node.did
    return ""


# --------------------------------------------------------------------------
# selector + config
# --------------------------------------------------------------------------


def test_selector_is_derived_from_the_verified_identity() -> None:
    did = "did:key:z6Mkqx6UVmFdZ3XiZQ7vTkZ2r8sXyN3abcXYZ"
    selector = contact_selector_for_did(did)
    assert selector.startswith("pcm/query/agent/")
    assert did[-16:] in selector or selector.rsplit("/", 1)[-1] == did[-16:]


def test_selector_rejects_a_non_did() -> None:
    with pytest.raises(ContactError):
        contact_selector_for_did("NooPunk")


def test_agent_names_are_distinct_per_node() -> None:
    """Issue #52: the three nodes must not collapse into one identity."""
    names = {agent_name_for(label) for label in ("Laskin", "lh6-725-37563", "NooPunk")}
    assert len(names) == 3
    assert agent_name_for("NooPunk") == "agent:hermes-noopunk"


def test_node_config_falls_back_to_a_distinct_identity_not_a_generic_one() -> None:
    config = load_node_config({})
    assert config.agent_name != "agent:hermes"
    assert config.agent_name.startswith("agent:hermes-")


def test_peers_are_parsed_from_the_environment() -> None:
    peers = peers_from_env("Laskin=192.0.2.10,lh6-725-37563=192.0.2.11:7447")
    assert [(p.label, p.host) for p in peers] == [
        ("Laskin", "192.0.2.10"),
        ("lh6-725-37563", "192.0.2.11:7447"),
    ]


def test_a_malformed_peer_entry_fails_loudly() -> None:
    """A typo'd peer must not be silently dropped; that would look like an unreachable host."""
    with pytest.raises(ValueError):
        peers_from_env("Laskin")


def test_no_peer_addresses_are_baked_into_the_code() -> None:
    """No operational address may be committed: unconfigured means no peers."""
    assert load_node_config({"PCM_NODE_LABEL": "NooPunk"}).peers == []


# --------------------------------------------------------------------------
# the round trip is the evidence
# --------------------------------------------------------------------------


def test_a_signed_contact_and_ack_prove_a_contact(tmp_path: Path) -> None:
    id_a, key_a, _ = make_identity(tmp_path, "a")
    id_b, key_b, _ = make_identity(tmp_path, "b")

    request = build_contact_request(
        sender_name="agent:hermes-a", sender_did=id_a["did"],
        recipient_name="agent:hermes-b", recipient_did=id_b["did"],
        node_label="A", note="hello from A",
    )
    request.sign(key_a, id_a["did"])
    ack = build_contact_ack(
        request=request, responder_name="agent:hermes-b", responder_did=id_b["did"],
        node_label="B", note="hello from B",
    )
    ack.sign(key_b, id_b["did"])

    evidence = verify_contact(request.model_dump(by_alias=True), ack.model_dump(by_alias=True))
    assert evidence.sender_label == "A"
    assert evidence.recipient_label == "B"
    assert evidence.request_id == request.id
    assert evidence.ack_id == ack.id
    assert evidence.verified


def test_an_ack_from_a_third_node_is_not_evidence(tmp_path: Path) -> None:
    """Direction matters: only the contacted node can prove it was contacted."""
    id_a, key_a, _ = make_identity(tmp_path, "a")
    id_b, key_b, _ = make_identity(tmp_path, "b")
    id_c, key_c, _ = make_identity(tmp_path, "c")

    request = build_contact_request(
        sender_name="agent:hermes-a", sender_did=id_a["did"],
        recipient_name="agent:hermes-b", recipient_did=id_b["did"], node_label="A",
    )
    request.sign(key_a, id_a["did"])
    # C answers a question that was put to B.
    impostor = build_contact_ack(
        request=request, responder_name="agent:hermes-c", responder_did=id_c["did"],
        node_label="C",
    )
    impostor.sign(key_c, id_c["did"])

    with pytest.raises(ContactError):
        verify_contact(request.model_dump(by_alias=True), impostor.model_dump(by_alias=True))


def test_an_ack_for_a_different_contact_is_not_evidence(tmp_path: Path) -> None:
    """Correlation: a stale or unrelated ack must not confirm a new contact."""
    id_a, key_a, _ = make_identity(tmp_path, "a")
    id_b, key_b, _ = make_identity(tmp_path, "b")

    def pair(note: str):
        req = build_contact_request(
            sender_name="agent:hermes-a", sender_did=id_a["did"],
            recipient_name="agent:hermes-b", recipient_did=id_b["did"],
            node_label="A", note=note,
        )
        req.sign(key_a, id_a["did"])
        ack = build_contact_ack(request=req, responder_name="agent:hermes-b",
                                responder_did=id_b["did"], node_label="B")
        ack.sign(key_b, id_b["did"])
        return req, ack

    first_req, first_ack = pair("first")
    second_req, _ = pair("second")
    with pytest.raises(ContactError):
        verify_contact(second_req.model_dump(by_alias=True),
                       first_ack.model_dump(by_alias=True))


def test_a_tampered_ack_is_not_evidence(tmp_path: Path) -> None:
    id_a, key_a, _ = make_identity(tmp_path, "a")
    id_b, key_b, _ = make_identity(tmp_path, "b")
    request = build_contact_request(
        sender_name="agent:hermes-a", sender_did=id_a["did"],
        recipient_name="agent:hermes-b", recipient_did=id_b["did"], node_label="A",
    )
    request.sign(key_a, id_a["did"])
    ack = build_contact_ack(request=request, responder_name="agent:hermes-b",
                            responder_did=id_b["did"], node_label="B")
    ack.sign(key_b, id_b["did"])

    tampered = ack.model_dump(by_alias=True)
    tampered["content"]["event"]["payload"]["note"] = "forged"
    with pytest.raises(ContactError):
        verify_contact(request.model_dump(by_alias=True), tampered)


def test_an_unsigned_contact_is_rejected(tmp_path: Path) -> None:
    id_a, _, _ = make_identity(tmp_path, "a")
    id_b, _, _ = make_identity(tmp_path, "b")
    request = build_contact_request(
        sender_name="agent:hermes-a", sender_did=id_a["did"],
        recipient_name="agent:hermes-b", recipient_did=id_b["did"], node_label="A",
    )
    with pytest.raises(ContactError):
        pc.accept_inbound_contact(request.model_dump(by_alias=True),
                                 expected_name="agent:hermes-b")


def test_a_contact_addressed_elsewhere_is_not_ours_to_answer(tmp_path: Path) -> None:
    id_a, key_a, _ = make_identity(tmp_path, "a")
    id_b, _, _ = make_identity(tmp_path, "b")
    request = build_contact_request(
        sender_name="agent:hermes-a", sender_did=id_a["did"],
        recipient_name="agent:hermes-b", recipient_did=id_b["did"], node_label="A",
    )
    request.sign(key_a, id_a["did"])
    with pytest.raises(ContactError):
        pc.accept_inbound_contact(request.model_dump(by_alias=True),
                                 expected_name="agent:hermes-c")


# --------------------------------------------------------------------------
# the matrix is built from evidence
# --------------------------------------------------------------------------


def _evidence(sender: str, recipient: str, **kwargs) -> pc.ContactEvidence:
    base = {
        "sender": f"agent:hermes-{sender.lower()}",
        "sender_label": sender,
        "sender_did": f"did:key:z{sender}",
        "recipient": f"agent:hermes-{recipient.lower()}",
        "recipient_label": recipient,
        "recipient_did": f"did:key:z{recipient}",
        "request_id": f"req-{sender}-{recipient}",
        "ack_id": f"ack-{sender}-{recipient}",
    }
    base.update(kwargs)
    return pc.ContactEvidence(**base)


def test_the_matrix_requires_all_six_directed_contacts() -> None:
    matrix = ContactMatrix(required=["Laskin", "lh6-725-37563", "NooPunk"])
    assert len(matrix.required_pairs()) == 6
    assert not matrix.complete
    matrix.record(_evidence("Laskin", "NooPunk"))
    assert matrix.status("Laskin", "NooPunk") == "confirmed"
    # the reverse direction is a different contact and is still missing
    assert matrix.status("NooPunk", "Laskin") == "missing"


def test_one_way_contact_is_not_enough() -> None:
    """The failure mode the issue names: 'all nodes visible' is not the matrix."""
    matrix = ContactMatrix(required=["Laskin", "NooPunk"])
    matrix.record(_evidence("Laskin", "NooPunk"))
    assert not matrix.complete
    assert matrix.missing_pairs() == [("NooPunk", "Laskin")]


def test_unverified_evidence_cannot_enter_the_matrix() -> None:
    matrix = ContactMatrix(required=["Laskin", "NooPunk"])
    assert matrix.record(_evidence("Laskin", "NooPunk", verified=False)) is False
    assert matrix.confirmed_pairs() == []


def test_a_contact_with_an_off_list_node_does_not_count() -> None:
    matrix = ContactMatrix(required=["Laskin", "NooPunk"])
    assert matrix.record(_evidence("Laskin", "RandomHost")) is False


def test_the_full_matrix_is_complete_and_reports_no_missing() -> None:
    nodes = ["Laskin", "lh6-725-37563", "NooPunk"]
    matrix = ContactMatrix(required=nodes)
    for a in nodes:
        for b in nodes:
            if a != b:
                matrix.record(_evidence(a, b))
    report = matrix.to_report()
    assert matrix.complete
    assert report["confirmed_count"] == 6
    assert report["missing"] == []
    assert report["matrix"]["Laskin"]["NooPunk"] == "confirmed"


def test_repeated_contact_with_a_peer_does_not_inflate_the_matrix() -> None:
    matrix = ContactMatrix(required=["Laskin", "NooPunk"])
    assert matrix.record(_evidence("Laskin", "NooPunk")) is True
    assert matrix.record(_evidence("Laskin", "NooPunk", request_id="again")) is False
    assert len(matrix.records) == 1


# --------------------------------------------------------------------------
# the whole exchange, end to end in-process
# --------------------------------------------------------------------------


def test_two_nodes_prove_contact_in_both_directions(tmp_path: Path) -> None:
    async def scenario():
        fabric = Fabric()
        a = await Node(tmp_path, "NooPunk", ["Laskin"], fabric).start()
        b = await Node(tmp_path, "Laskin", ["NooPunk"], fabric).start()
        wire_peer_dids(a, b)

        forward = await a.node.contact("Laskin", note="hello from NooPunk", timeout=2.0)
        backward = await b.node.contact("NooPunk", note="hello from Laskin", timeout=2.0)

        assert (forward.sender_label, forward.recipient_label) == ("NooPunk", "Laskin")
        assert (backward.sender_label, backward.recipient_label) == ("Laskin", "NooPunk")
        # the responder recorded the inbound contact it answered
        assert b.node.inbound and b.node.inbound[0]["from"] == a.node.agent_name
        await a.transport.stop()
        await b.transport.stop()

    asyncio.run(scenario())


def test_an_unanswered_contact_is_a_failure_not_a_success(tmp_path: Path) -> None:
    """A request nobody answers has not been delivered, and must not read as contact."""
    async def scenario():
        fabric = Fabric()
        a = await Node(tmp_path, "NooPunk", ["Laskin"], fabric).start()
        # B is on the fabric but is not serving: visible, not contactable.
        b = await Node(tmp_path, "Laskin", ["NooPunk"], fabric).start(serve=False)
        wire_peer_dids(a, b)
        with pytest.raises(CoordinationError):
            await a.node.contact("Laskin", timeout=0.5)
        await a.transport.stop()

    asyncio.run(scenario())


def test_contacting_an_unconfigured_peer_is_an_error(tmp_path: Path) -> None:
    async def scenario():
        a = await Node(tmp_path, "NooPunk", ["Laskin"]).start()
        with pytest.raises(CoordinationError):
            await a.node.contact("NeverHeardOfIt")
        await a.transport.stop()

    asyncio.run(scenario())


def test_contact_without_a_known_did_is_refused(tmp_path: Path) -> None:
    """Contacting a bare address cannot be verified, so it is refused."""
    async def scenario():
        a = await Node(tmp_path, "NooPunk", ["Laskin"]).start()
        with pytest.raises(CoordinationError):
            await a.node.contact("Laskin")
        await a.transport.stop()

    asyncio.run(scenario())


def test_contact_all_reports_per_peer_without_aborting(tmp_path: Path) -> None:
    async def scenario():
        fabric = Fabric()
        a = await Node(tmp_path, "NooPunk", ["Laskin", "lh6-725-37563"], fabric).start()
        b = await Node(tmp_path, "Laskin", ["NooPunk"], fabric).start()
        a.node.config.peers = [
            PeerConfig(label="Laskin", host="127.0.0.1", did=b.did),
            PeerConfig(label="lh6-725-37563", host="127.0.0.1", did="did:key:zAbsentNode"),
        ]
        results = await a.node.contact_all(timeout=0.5)
        assert results["Laskin"]["status"] == "confirmed"
        assert results["lh6-725-37563"]["status"] == "missing"
        await a.transport.stop()
        await b.transport.stop()

    asyncio.run(scenario())


def test_answering_a_contact_confers_no_authority(tmp_path: Path) -> None:
    """Reachability is not authorization: an ack performs no action for the peer."""
    async def scenario():
        fabric = Fabric()
        a = await Node(tmp_path, "NooPunk", ["Laskin"], fabric).start()
        b = await Node(tmp_path, "Laskin", ["NooPunk"], fabric).start()
        wire_peer_dids(a, b)
        before = len(b.node.inbound)
        await a.node.contact("Laskin", timeout=2.0)
        # B recorded the contact and answered it; nothing else happened on B.
        assert len(b.node.inbound) == before + 1
        assert b.node.store.load() == []  # B holds no outbound evidence from answering
        await a.transport.stop()
        await b.transport.stop()

    asyncio.run(scenario())


# --------------------------------------------------------------------------
# evidence stores and the ledger
# --------------------------------------------------------------------------


def test_evidence_is_persisted_once(tmp_path: Path) -> None:
    store = ContactStore(tmp_path / "contacts.json")
    assert store.append(_evidence("NooPunk", "Laskin")) is True
    assert store.append(_evidence("NooPunk", "Laskin")) is False
    assert len(store.load()) == 1


def test_a_corrupt_evidence_file_is_an_error_not_an_empty_store(tmp_path: Path) -> None:
    """A broken evidence file must not read as 'no contacts'."""
    path = tmp_path / "contacts.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        ContactStore(path).load()


def test_the_ledger_merges_stores_without_double_counting(tmp_path: Path) -> None:
    """Two nodes holding the same directed contact is one contact, not two."""
    a = ContactStore(tmp_path / "a.json")
    b = ContactStore(tmp_path / "b.json")
    a.append(_evidence("Laskin", "NooPunk"))
    b.append(_evidence("Laskin", "NooPunk"))  # the same contact, seen from the other end

    ledger = ContactLedger(required=["Laskin", "NooPunk"])
    assert ledger.add_stores([a, b]) == 1
    assert ledger.matrix.confirmed_pairs() == [("Laskin", "NooPunk")]


def test_the_report_is_generated_from_evidence_only(tmp_path: Path) -> None:
    store = ContactStore(tmp_path / "contacts.json")
    store.append(_evidence("NooPunk", "Laskin"))
    ledger = ContactLedger(required=["Laskin", "lh6-725-37563", "NooPunk"])
    ledger.add_store(store)
    report = ledger.report()

    assert report["kind"] == "pcm.contact_report/1"
    assert report["complete"] is False
    assert report["confirmed_count"] == 1
    assert report["required_count"] == 6
    assert {"from": "NooPunk", "to": "Laskin"} not in report["missing"]
    assert {"from": "Laskin", "to": "NooPunk"} in report["missing"]
    assert report["evidence"][0]["request_id"] == "req-NooPunk-Laskin"


def test_the_report_serializes_to_json(tmp_path: Path) -> None:
    store = ContactStore(tmp_path / "contacts.json")
    store.append(_evidence("NooPunk", "Laskin"))
    ledger = ContactLedger(required=["Laskin", "NooPunk"])
    ledger.add_store(store)
    text = json.dumps(ledger.report())
    assert "pcm.contact_report/1" in text


def test_a_peer_did_is_public_material_not_a_secret() -> None:
    """The peer-did mapping is identity, not credential; a did:key has no secret."""
    identity, _, _ = make_identity(Path("/tmp") / "pcm-did-probe", "n")
    assert identity["did"].startswith("did:key:z")
    assert "secret" not in identity["did"].lower()
