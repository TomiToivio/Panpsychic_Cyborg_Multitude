# -*- coding: utf-8 -*-
"""Issue #52 — the operator view of identities learned from inbound contacts.

Main persists learned peer dids (`peer_dids.json`, applied in
``_apply_learned_peer_dids``) and uses them to fill a missing peer did. Two things
were still missing, and both are things issue #52 asks for explicitly:

1. **"surface current peer/contact status to the Hermes operator."** The cache was
   an internal file. Nothing could answer *"who has contacted me, and what did I
   learn from it?"* without opening the JSON by hand, and `status` reported only
   ``did_known`` -- so a did the operator configured and a did learned from a
   contact looked identical.
2. **"keep sensitive material out / identity and authority separable."** The same
   surface has to make the *provenance* of a did visible, because "I chose this
   address" and "a peer told me this address" carry different weight when deciding
   whether to dial it.

These tests drive a real inbound contact through the real cache and then assert
what the operator surface reports, rather than hand-writing a cache fixture -- a
fixture would pass even if the writer and the reader disagreed about the format.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_pcm_coordination import Fabric, Node, make_identity, wire_peer_dids  # noqa: E402

from multitude.integrations.hermes.coordination_adapter import (  # noqa: E402
    CoordinationNode,
)
from multitude.integrations.hermes.coordination import NodeConfig, PeerConfig  # noqa: E402


def _node_with_cache(tmp: Path, label: str, peers: list[str], cache: dict | None,
                     configured: dict[str, str] | None = None) -> CoordinationNode:
    """A node whose learned cache is pre-seeded, for read-surface tests.

    ``cache=None`` writes nothing, which is the normal state of a node that has
    never been contacted. A cache written here must use the real on-disk shape
    (``{"schema": ..., "peers": {...}}``): anything else is malformed by
    definition, so passing a bare ``{}`` would be testing the corrupt path.
    """
    identity, _key, directory = make_identity(tmp, label)
    (directory / "coordination").mkdir(parents=True, exist_ok=True)
    if cache is not None:
        (directory / "coordination" / "peer_dids.json").write_text(
            json.dumps(cache), encoding="utf-8"
        )
    return CoordinationNode(
        _NoopTransport(),
        node_dir=directory,
        config=NodeConfig(
            label=label,
            agent_name=f"agent:hermes-{label.lower()}",
            peers=[
                PeerConfig(label=p, host="127.0.0.1",
                           did=(configured or {}).get(p, ""))
                for p in peers
            ],
        ),
    )


class _NoopTransport:
    """A transport stub: these tests exercise the read surface, not the wire."""

    async def start(self) -> None:  # pragma: no cover - unused
        pass

    async def stop(self) -> None:  # pragma: no cover - unused
        pass


# --- the surface exists and is honest about provenance ------------------------


def test_a_learned_peer_is_visible_after_a_real_inbound_contact(tmp_path: Path) -> None:
    """The end-to-end reading, driven through the real writer."""
    import asyncio

    async def scenario():
        fabric = Fabric()
        a = await Node(tmp_path, "lh6-725-37563", ["NooPunk"], fabric).start()
        b = await Node(tmp_path, "NooPunk", ["lh6-725-37563"], fabric).start()
        wire_peer_dids(a, b)
        try:
            await a.node.contact("NooPunk", note="hello", timeout=2.0)
            return a.did
        finally:
            await a.transport.stop()
            await b.transport.stop()

    sender_did = asyncio.run(scenario())

    # b's own view of what it learned
    b_dir = tmp_path / "NooPunk"
    node = CoordinationNode(
        _NoopTransport(),
        node_dir=b_dir,
        config=NodeConfig(
            label="NooPunk",
            agent_name="agent:hermes-noopunk",
            peers=[PeerConfig(label="lh6-725-37563", host="127.0.0.1")],
        ),
    )
    learned = node.learned_peer_dids()
    assert "lh6-725-37563" in learned, "the inbound peer is not visible to the operator"
    assert learned["lh6-725-37563"].did == sender_did
    assert learned["lh6-725-37563"].to_dict()["source"] == "verified inbound contact"


def test_did_source_distinguishes_configured_from_learned(tmp_path: Path) -> None:
    """`did_known` alone cannot tell these apart, which is why this exists."""
    node = _node_with_cache(
        tmp_path,
        "NooPunk",
        ["Laskin", "lh6-725-37563"],
        {"schema": "pcm.learned-peer-dids/1",
         "peers": {"lh6-725-37563": "did:key:zLearnedOnly"}},
        configured={"Laskin": "did:key:zConfigured"},
    )
    sources = {p["label"]: p["did_source"] for p in node.status()["peers"]}
    assert sources["Laskin"] == "configured"
    assert sources["lh6-725-37563"] == "learned-from-inbound-contact"


def test_a_configured_did_beats_a_learned_one_in_the_report(tmp_path: Path) -> None:
    """The surface must describe the precedence the node actually applies."""
    node = _node_with_cache(
        tmp_path,
        "NooPunk",
        ["Laskin"],
        {"schema": "pcm.learned-peer-dids/1",
         "peers": {"Laskin": "did:key:zLearned"}},
        configured={"Laskin": "did:key:zConfigured"},
    )
    entry = node.status()["peers"][0]
    assert entry["did_source"] == "configured"
    assert entry["did_known"] is True


def test_a_peer_with_no_did_reports_unknown(tmp_path: Path) -> None:
    """A node that has never been contacted knows no peer dids."""
    node = _node_with_cache(tmp_path, "NooPunk", ["Laskin"], None)
    entry = node.status()["peers"][0]
    assert entry["did_known"] is False
    assert entry["did_source"] == "unknown"


def test_status_exposes_the_learned_list(tmp_path: Path) -> None:
    node = _node_with_cache(
        tmp_path,
        "NooPunk",
        ["lh6-725-37563"],
        {"schema": "pcm.learned-peer-dids/1",
         "peers": {"lh6-725-37563": "did:key:zLearned"}},
    )
    learned = node.status()["learned_peers"]
    assert len(learned) == 1
    assert learned[0]["label"] == "lh6-725-37563"


# --- a broken cache must not read as "nothing learned" ------------------------


def test_a_corrupt_cache_reports_an_error_not_an_empty_list(tmp_path: Path) -> None:
    """Reading a corrupt cache as empty would silently hide a contactable peer."""
    node = _node_with_cache(tmp_path, "NooPunk", ["Laskin"], None)
    path = node.node_dir / "coordination" / "peer_dids.json"
    path.write_text("{not json", encoding="utf-8")

    result = node.learned_peer_dids()
    assert "error" in result, "a corrupt cache was reported as an empty result"


def test_a_wrongly_shaped_cache_reports_an_error(tmp_path: Path) -> None:
    node = _node_with_cache(tmp_path, "NooPunk", ["Laskin"], None)
    path = node.node_dir / "coordination" / "peer_dids.json"
    path.write_text(json.dumps({"peers": ["not", "a", "mapping"]}), encoding="utf-8")

    result = node.learned_peer_dids()
    assert "error" in result


def test_a_missing_cache_is_simply_empty(tmp_path: Path) -> None:
    """Absent is not broken: a node that has learned nothing is the normal start."""
    node = _node_with_cache(tmp_path, "NooPunk", ["Laskin"], None)
    assert node.learned_peer_dids() == {}


def test_a_status_survives_an_unreadable_cache(tmp_path: Path) -> None:
    """The status command must still report everything else it knows."""
    node = _node_with_cache(tmp_path, "NooPunk", ["Laskin"], None)
    (node.node_dir / "coordination" / "peer_dids.json").write_text("{oops", encoding="utf-8")
    status = node.status()
    assert status["learned_peers"] == []
    assert status["learned_peers_error"], "the error was swallowed"
    assert status["node_label"] == "NooPunk"


# --- identity only: no authority leaks into the read surface ------------------


def test_the_read_view_carries_no_authority_shaped_field() -> None:
    from multitude.integrations.hermes.coordination_adapter import LearnedPeerView

    fields = set(LearnedPeerView.__dataclass_fields__)
    assert fields == {"label", "did", "first_seen", "last_seen"}
    for forbidden in ("permission", "capability", "authority", "admin", "grant", "role"):
        assert not any(forbidden in f for f in fields), f"{forbidden!r} leaked in"


def test_the_read_view_exposes_only_the_public_did(tmp_path: Path) -> None:
    """A did:key is the public half; the seed must never appear in this surface."""
    node = _node_with_cache(
        tmp_path, "NooPunk", ["Laskin"],
        {"schema": "pcm.learned-peer-dids/1", "peers": {"Laskin": "did:key:zPublic"}},
        configured={"Laskin": "did:key:zPublic"},
    )
    dumped = json.dumps(node.status()).lower()
    for forbidden in ("private", "seed", "secret", "-----begin"):
        assert forbidden not in dumped
