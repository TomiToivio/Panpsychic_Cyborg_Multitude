# -*- coding: utf-8 -*-
"""Issue #52 — the HTTP/JSON coordination binding and its route isolation.

ADR-001 selects an isolated HTTP/JSON endpoint as the first runtime transport, with
route isolation as a *requirement* rather than a follow-up: a peer able to send a
coordination envelope must not thereby reach PCM's service-mutation surface.

These tests are the enforcement of that. They use the merged protocol unchanged
(``pcm.contact`` / ``CoordinationNode``) over a real loopback HTTP listener, so
they exercise the wire path without needing the three live machines — which is
what the issue asks of CI.

Deliberately excluded from "contact" here: a bare TCP connect, a reachable port, or
two things in one process. The isolation tests are negative tests and assert the
absence of a capability, because a missing route is the security property.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.integrations.coordination.http_transport import (  # noqa: E402
    COORDINATION_PATH,
    SELECTOR_HEADER,
    HttpJsonTransport,
)
from multitude.integrations.hermes.coordination import (  # noqa: E402
    NodeConfig,
    PeerConfig,
    agent_name_for,
)
from multitude.integrations.hermes.coordination_adapter import CoordinationNode  # noqa: E402
from multitude.pcm.contact import contact_selector_for_did  # noqa: E402
from multitude.pcm.identity import generate_identity  # noqa: E402


def _http_node(tmp: Path, label: str, peers: list[str], port: int):
    """A CoordinationNode whose transport is the HTTP/JSON listener."""
    directory = tmp / label
    directory.mkdir(parents=True, exist_ok=True)
    generate_identity(str(directory))
    transport = HttpJsonTransport(
        {"pcm_id": agent_name_for(label)}, listen_host="127.0.0.1", listen_port=port
    )
    node = CoordinationNode(
        transport,
        node_dir=directory,
        config=NodeConfig(
            label=label,
            agent_name=agent_name_for(label),
            peers=[PeerConfig(label=p, host="127.0.0.1") for p in peers],
        ),
    )
    return node


def test_contact_over_http_json_between_two_nodes(tmp_path: Path) -> None:
    """The protocol rides the HTTP binding: request, correlated ack, evidence."""

    async def scenario() -> None:
        # Distinct loopback ports = two distinct endpoints, as two hosts would be.
        requester = _http_node(tmp_path, "Laskin", ["NooPunk"], port=0)
        responder = _http_node(tmp_path, "NooPunk", ["Laskin"], port=0)

        await requester.transport.start()
        await responder.transport.start()
        try:
            await requester.start_serving()
            await responder.start_serving()

            responder_host, responder_port = responder.transport.bound_address
            responder_url = f"http://{responder_host}:{responder_port}"

            requester.config.peers = [
                PeerConfig(label="NooPunk", host=responder_url, did=responder.did)
            ]

            # The transport takes the peer URL per call; addressing lives in the
            # deployment, not in the protocol binding.
            original_request = requester.transport.request

            async def request_with_peer_url(selector, payload=None, timeout=5.0):
                return await original_request(
                    selector, payload, timeout, peer_url=responder_url
                )

            requester.transport.request = request_with_peer_url  # type: ignore[method-assign]

            evidence = await requester.contact("NooPunk", note="http binding", timeout=6.0)

            assert evidence.verified is True
            assert (evidence.sender_label, evidence.recipient_label) == (
                "Laskin",
                "NooPunk",
            )
            # the responder really received and answered THIS request
            assert any(
                item["request_id"] == evidence.request_id for item in responder.inbound
            )
            # and the ack correlates to the request, not to some other contact
            assert evidence.ack_id != evidence.request_id
        finally:
            await requester.transport.stop()
            await responder.transport.stop()

    asyncio.run(scenario())


def test_a_request_nobody_answers_is_not_a_contact(tmp_path: Path) -> None:
    """Fail closed: an unanswered request raises rather than reporting success."""

    async def scenario() -> None:
        node = _http_node(tmp_path, "Laskin", ["NooPunk"], port=0)
        await node.transport.start()
        try:
            # a live listener that has declared NO queryable
            silent = _http_node(tmp_path, "Silent", [], port=0)
            await silent.transport.start()
            host, port = silent.transport.bound_address
            url = f"http://{host}:{port}"

            node.config.peers = [
                PeerConfig(label="NooPunk", host=url, did=silent.did)
            ]
            original_request = node.transport.request

            async def with_url(selector, payload=None, timeout=5.0):
                return await original_request(selector, payload, timeout, peer_url=url)

            node.transport.request = with_url  # type: ignore[method-assign]

            from multitude.integrations.hermes.coordination_adapter import (
                CoordinationError,
            )

            with pytest.raises(CoordinationError):
                await node.contact("NooPunk", timeout=3.0)
            await silent.transport.stop()
        finally:
            await node.transport.stop()

    asyncio.run(scenario())


# --- route isolation (issue #52 §3, ADR-001: a requirement, not a follow-up) ---


def test_service_mutation_routes_are_unreachable_through_the_coordination_listener(
    tmp_path: Path,
) -> None:
    """The narrow door: only the coordination route exists on this listener.

    A peer that can send a coordination envelope must not reach
    /api/proposals|votes|counsel|memory. This asserts the absence, because the
    absence IS the security property.
    """
    node = _http_node(tmp_path, "Laskin", [], port=0)

    async def start() -> None:
        await node.transport.start()
        await node.start_serving()

    asyncio.run(start())
    try:
        host, port = node.transport.bound_address
        base = f"http://{host}:{port}"
        mutation_paths = [
            "/api/proposals",
            "/api/votes",
            "/api/counsel",
            "/api/memory",
            "/api/status",
            "/api/agents",
            "/api/search",
            "/coordination/v1/",
            "/",
        ]
        for path in mutation_paths:
            req = urllib_request.Request(
                base + path,
                data=json.dumps({"probe": True}).encode(),
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with pytest.raises(urllib_error.HTTPError) as excinfo:
                urllib_request.urlopen(req, timeout=3)
            # 404: the route does not exist here. Not 401/403 (which would mean
            # the route exists and merely refused), and never 200.
            assert excinfo.value.code == 404, f"{path} answered {excinfo.value.code}"

        # GET must not fall through to anything either.
        with pytest.raises(urllib_error.HTTPError) as excinfo:
            urllib_request.urlopen(base + "/api/proposals", timeout=3)
        assert excinfo.value.code in (404, 501)
    finally:
        asyncio.run(node.transport.stop())


def test_coordination_route_requires_the_selector_header(tmp_path: Path) -> None:
    """Without the addressing header the route refuses — no default destination."""
    node = _http_node(tmp_path, "Laskin", [], port=0)

    async def start() -> None:
        await node.transport.start()
        await node.start_serving()

    asyncio.run(start())
    try:
        host, port = node.transport.bound_address
        req = urllib_request.Request(
            f"http://{host}:{port}{COORDINATION_PATH}",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib_error.HTTPError) as excinfo:
            urllib_request.urlopen(req, timeout=3)
        assert excinfo.value.code == 400
    finally:
        asyncio.run(node.transport.stop())


def test_a_misaddressed_contact_gets_silence_not_an_ack(tmp_path: Path) -> None:
    """contact_handler fails closed: wrong recipient -> no ack, and a reason.

    The refusal must not look like a wrong address. A 404 means "no queryable
    here"; a declined-but-registered selector is a distinct outcome, because
    conflating them once sent a peer agent chasing the wrong cause.
    """
    node = _http_node(tmp_path, "Laskin", [], port=0)

    async def start() -> None:
        await node.transport.start()
        await node.start_serving()

    asyncio.run(start())
    try:
        host, port = node.transport.bound_address
        # addressed to a DIFFERENT node's selector than the one serving
        wrong_selector = contact_selector_for_did("did:key:zWrongRecipient")
        req = urllib_request.Request(
            f"http://{host}:{port}{COORDINATION_PATH}",
            data=json.dumps({"not": "a valid envelope"}).encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                SELECTOR_HEADER: wrong_selector,
            },
        )
        with pytest.raises(urllib_error.HTTPError) as excinfo:
            urllib_request.urlopen(req, timeout=3)
        # an unregistered selector really is a 404
        assert excinfo.value.code == 404
    finally:
        asyncio.run(node.transport.stop())


def test_a_registered_selector_that_declines_is_distinguishable(tmp_path: Path) -> None:
    """A registered selector with a bad envelope must NOT report 'wrong address'.

    This is the regression for the diagnostic conflation: both cases returned
    `no queryable for selector` / 404, so a caller could not tell a correct
    fail-closed refusal from a misconfigured address.
    """
    node = _http_node(tmp_path, "Laskin", [], port=0)

    async def start() -> None:
        await node.transport.start()
        await node.start_serving()

    asyncio.run(start())
    try:
        host, port = node.transport.bound_address
        own_selector = contact_selector_for_did(node.did)
        req = urllib_request.Request(
            f"http://{host}:{port}{COORDINATION_PATH}",
            data=json.dumps({"not": "a valid envelope"}).encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                SELECTOR_HEADER: own_selector,
            },
        )
        with pytest.raises(urllib_error.HTTPError) as excinfo:
            urllib_request.urlopen(req, timeout=3)
        # registered, so it is not "no queryable"; it declined
        assert excinfo.value.code == 403
        body = json.loads(excinfo.value.read().decode())
        assert "refused" in body.get("error", "")
    finally:
        asyncio.run(node.transport.stop())


def test_transport_satisfies_the_abc() -> None:
    """It is a binding behind the existing seam, not a new subsystem."""
    from multitude.pcm.transport import Transport

    transport = HttpJsonTransport({"pcm_id": "agent:hermes-laskin"})
    assert isinstance(transport, Transport)
    for method in (
        "start",
        "stop",
        "publish",
        "subscribe",
        "request",
        "register_queryable",
        "get_identity",
    ):
        assert hasattr(transport, method), method


def test_identity_is_per_node_not_generic() -> None:
    """Issue #52: the three nodes must not collapse into one agent:hermes."""
    a = HttpJsonTransport({"pcm_id": "agent:hermes-laskin"})
    b = HttpJsonTransport({"pcm_id": "agent:hermes-noopunk"})
    assert asyncio.run(a.get_identity()) != asyncio.run(b.get_identity())


def test_listener_binds_only_the_requested_interface(tmp_path: Path) -> None:
    """Minimal exposed surface: the listener binds what it was told, nothing wilder."""
    transport = HttpJsonTransport(
        {"pcm_id": "agent:hermes-laskin"}, listen_host="127.0.0.1", listen_port=0
    )

    async def start() -> None:
        await transport.start()

    asyncio.run(start())
    try:
        host, _port = transport.bound_address
        assert host == "127.0.0.1", f"bound {host}, expected loopback"
    finally:
        asyncio.run(transport.stop())


# --- the CLI can actually serve and contact over B (issue #52 Step 3/4) ---


def test_cli_selects_the_http_transport_and_builds_peer_urls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PCM_COORDINATION_TRANSPORT=http must produce the HTTP binding end to end.

    The protocol calls request(selector) with no URL — it must not know about
    transports — so the CLI is responsible for handing the binding an address
    book keyed by the selector the contact layer actually uses.
    """
    import argparse

    from multitude.integrations.coordination.http_transport import HttpJsonTransport
    from multitude.integrations.hermes import coordination_cli

    peer_did = "did:key:z6Mkmwr2Z3YFU9pge2NTQUHFqLf8EhLoJsonL4dZeMs9WvQ5"
    monkeypatch.setenv("PCM_COORDINATION_TRANSPORT", "http")
    monkeypatch.setenv("PCM_COORDINATION_LISTEN", "127.0.0.1:8789")
    monkeypatch.setenv("PCM_NODE_LABEL", "Laskin")
    monkeypatch.setenv("PCM_AGENT_NAME", "agent:hermes-laskin")
    monkeypatch.setenv("PCM_NODE_DIR", str(tmp_path / "laskin"))
    monkeypatch.setenv("PCM_PEERS", "NooPunk=127.0.0.1:8790")
    monkeypatch.setenv("PCM_PEER_DIDS", f"NooPunk={peer_did}")

    args = argparse.Namespace(label=None, node_dir=None, store=None)
    node = coordination_cli._build_node(args)

    assert isinstance(node.transport, HttpJsonTransport)
    # the peer URL was normalised to a full URL, and is resolvable by selector
    peer = node.config.peer("NooPunk")
    assert peer is not None and peer.host == "http://127.0.0.1:8790"
    assert node.transport._peer_urls[contact_selector_for_did(peer_did)] == (
        "http://127.0.0.1:8790"
    )
    assert node.transport.bound_address is None  # not started yet


def test_cli_rejects_a_bad_listen_spec(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A malformed address must fail loudly, not bind nothing and look healthy."""
    import argparse

    from multitude.integrations.hermes import coordination_cli

    monkeypatch.setenv("PCM_COORDINATION_TRANSPORT", "http")
    monkeypatch.setenv("PCM_COORDINATION_LISTEN", "not-an-address")
    monkeypatch.setenv("PCM_NODE_DIR", str(tmp_path / "n"))

    with pytest.raises(SystemExit):
        coordination_cli._build_node(
            argparse.Namespace(label=None, node_dir=None, store=None)
        )


def test_cli_rejects_an_unknown_transport(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import argparse

    from multitude.integrations.hermes import coordination_cli

    monkeypatch.setenv("PCM_COORDINATION_TRANSPORT", "carrier-pigeon")
    monkeypatch.setenv("PCM_NODE_DIR", str(tmp_path / "n"))

    with pytest.raises(SystemExit):
        coordination_cli._build_node(
            argparse.Namespace(label=None, node_dir=None, store=None)
        )


def test_cli_outbound_mode_does_not_bind_the_listener(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A contact process can run while the dedicated serve process owns the port."""
    import argparse

    from multitude.integrations.hermes import coordination_cli

    peer_did = "did:key:z6Mkmwr2Z3YFU9pge2NTQUHFqLf8EhLoJsonL4dZeMs9WvQ5"
    monkeypatch.setenv("PCM_COORDINATION_TRANSPORT", "http")
    monkeypatch.setenv("PCM_COORDINATION_LISTEN", "127.0.0.1:8789")
    monkeypatch.setenv("PCM_NODE_LABEL", "Laskin")
    monkeypatch.setenv("PCM_AGENT_NAME", "agent:hermes-laskin")
    monkeypatch.setenv("PCM_NODE_DIR", str(tmp_path / "laskin"))
    monkeypatch.setenv("PCM_PEERS", "NooPunk=127.0.0.1:8790")
    monkeypatch.setenv("PCM_PEER_DIDS", f"NooPunk={peer_did}")

    node = coordination_cli._build_node(
        argparse.Namespace(label=None, node_dir=None, store=None),
        enable_listener=False,
    )

    assert node.transport._listen_host is None
    assert node.transport._listen_port is None
    assert node.transport.bound_address is None
    assert node.transport._peer_urls[contact_selector_for_did(peer_did)] == (
        "http://127.0.0.1:8790"
    )


def test_cli_outbound_http_does_not_require_a_listen_address(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit HTTP outbound use needs peer addresses, not a local server socket."""
    import argparse

    from multitude.integrations.hermes import coordination_cli

    monkeypatch.setenv("PCM_COORDINATION_TRANSPORT", "http")
    monkeypatch.delenv("PCM_COORDINATION_LISTEN", raising=False)
    monkeypatch.setenv("PCM_NODE_DIR", str(tmp_path / "n"))

    node = coordination_cli._build_node(
        argparse.Namespace(label=None, node_dir=None, store=None),
        enable_listener=False,
    )
    assert node.transport._listen_host is None
    assert node.transport._listen_port is None
