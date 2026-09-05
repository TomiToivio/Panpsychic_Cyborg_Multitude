# -*- coding: utf-8 -*-
"""ZenohTransport — Zenoh implementation of the generic PCM Transport.

Implements multitude.pcm.transport.Transport over Eclipse Zenoh
(verified against eclipse-zenoh 1.10.0, Python 3.12, 2026-09):

- pub/sub for realtime events (messages, telemetry, presence, state)
- queryables for request/response (queries against agents/devices/memory)
- liveliness tokens for node presence (agent/device online semantics)

Topology: default ``mode="peer"`` — nodes find each other via UDP
multicast scouting on the LAN, no central server. ``mode="client"``
connects through one or more Zenoh routers (infrastructure optimization
for WAN/NAT, never an authority). Configuration comes from kwargs or
environment: ``PCM_ZENOH_CONNECT`` (comma-separated router locators)
switches a session to client mode.

The transport carries JSON dicts; semantics live in pcm.events /
pcm.policy. Verification of signed envelopes happens in the adapter
layer that sits on top of this fabric (envelope.verify before dispatch).
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
from typing import Any

from multitude.pcm.namespace import validate_key
from multitude.pcm.transport import Transport, TransportError

DEFAULT_TRIBE = "default"


class ZenohTransportConfigError(RuntimeError):
    """Zenoh fabric is misconfigured."""


def _build_zenoh_config(mode: str, connect: list[str], listen: list[str]):
    import zenoh
    cfg = zenoh.Config()
    if mode == "client" or connect:
        cfg.insert_json5("mode", json.dumps("client"))
        if connect:
            cfg.insert_json5("connect/endpoints", json.dumps(connect))
    else:
        cfg.insert_json5("mode", json.dumps("peer"))
        cfg.insert_json5("scouting/multicast/enabled", json.dumps(True))
        if listen:
            cfg.insert_json5("listen/endpoints/peer", json.dumps(listen))
    return cfg


class ZenohTransport(Transport):
    """One PCM node's Zenoh session implementing the generic interface."""

    def __init__(self, identity: dict[str, Any] | None = None, *,
                 mode: str = "peer",
                 connect_endpoints: list[str] | None = None,
                 listen_endpoints: list[str] | None = None) -> None:
        self._identity = identity or {"pcm_id": "agent:local"}
        connect = connect_endpoints
        if connect is None:
            env_connect = [e for e in os.environ.get("PCM_ZENOH_CONNECT", "").split(",") if e.strip()]
            connect = env_connect or None
            if connect:
                mode = "client"
        self._mode = mode
        self._connect = connect or []
        self._listen = listen_endpoints or []
        self._session: Any = None
        self._tokens: list[Any] = []       # undeclarables (subs, tokens)
        self._started = False

    # -- lifecycle ------------------------------------------------------------

    async def start(self) -> None:
        import zenoh
        self._session = zenoh.open(_build_zenoh_config(
            self._mode, self._connect, self._listen))
        self._started = True
        # presence: one liveliness token under pcm/liveliness/<kind>/<name>
        pcm_id = str(self._identity.get("pcm_id", ""))
        if ":" in pcm_id:
            kind, name = pcm_id.split(":", 1)
            try:
                token = self._session.liveliness().declare_token(
                    validate_key(f"pcm/liveliness/{kind}/{name}"))
                self._tokens.append(token)
            except Exception:
                pass  # liveliness is presence sugar, never load-bearing

    async def stop(self) -> None:
        for t in self._tokens:
            try:
                t.undeclare()
            except Exception:
                pass
        self._tokens.clear()
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
        self._session = None
        self._started = False

    def _require_started(self) -> None:
        if not self._started or self._session is None:
            raise TransportError("transport not started; call start() first")

    # -- async-bridge helper -----------------------------------------------------

    def _run_async(self, coro, done) -> None:
        """Run an async handler on a private loop thread and deliver its
        result through ``done``. Zenoh callbacks are sync; this bridges
        async application code onto them."""
        def _worker() -> None:
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(coro)
                done(result)
            except Exception:
                pass
            finally:
                loop.close()

        threading.Thread(target=_worker, daemon=True).start()

    # -- pub/sub ----------------------------------------------------------------

    async def publish(self, topic: str, event: dict[str, Any]) -> None:
        self._require_started()
        validate_key(topic)
        payload = json.dumps(event, ensure_ascii=False).encode("utf-8")
        self._session.put(topic, payload)

    async def subscribe(self, pattern: str, handler: Any) -> Any:
        self._require_started()
        validate_key(pattern, allow_wildcards=True)

        def _on_sample(sample) -> None:
            try:
                data = json.loads(bytes(sample.payload))
            except Exception:
                return  # malformed payloads die at the edge
            try:
                result = handler(data, str(sample.key_expr))
                if asyncio.iscoroutine(result):
                    # fire-and-forget: async subscriber handlers run on
                    # their own loop; errors never surface here
                    self._run_async(result, lambda _r: None)
            except Exception:
                pass  # handler errors never kill the fabric thread

        sub = self._session.declare_subscriber(pattern, _on_sample)
        self._tokens.append(sub)
        return sub

    # -- request/response ---------------------------------------------------------

    async def register_queryable(self, selector: str, handler: Any) -> Any:
        self._require_started()
        validate_key(selector)

        def _on_query(query) -> None:
            try:
                raw = bytes(query.payload) if query.payload is not None else None
                request = json.loads(raw) if raw else None
            except Exception:
                request = None

            def _finish(reply) -> None:
                if reply is None:
                    return
                try:
                    query.reply(query.key_expr,
                                json.dumps(reply, ensure_ascii=False).encode("utf-8"))
                except Exception:
                    pass

            try:
                result = handler(request, str(query.key_expr))
                if asyncio.iscoroutine(result):
                    self._run_async(result, _finish)
                else:
                    _finish(result)
            except Exception:
                try:
                    query.reply_err(b"queryable handler failed")
                except Exception:
                    pass

        q = self._session.declare_queryable(selector, _on_query)
        self._tokens.append(q)
        return q

    async def request(self, selector: str,
                      payload: dict[str, Any] | None = None,
                      timeout: float = 5.0) -> list[dict[str, Any]]:
        self._require_started()
        validate_key(selector, allow_wildcards=True)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        replies: list[dict[str, Any]] = []
        channel = self._session.get(selector, payload=body, timeout=timeout)
        while True:
            try:
                r = channel.recv()
            except Exception:
                break  # channel closed: query finished
            if r.ok:
                try:
                    replies.append(json.loads(bytes(r.result.payload)))
                except Exception:
                    continue  # unparseable replies never surface
            else:
                break  # error reply terminates the query
        return replies

    # -- presence ------------------------------------------------------------------

    async def watch_liveliness(self, pattern: str, on_change: Any) -> Any:
        """Subscribe to Zenoh liveliness changes for a PCM liveliness pattern.

        ``on_change(name: str, alive: bool)`` fires on token PUT (alive)
        and DELETE (gone) samples.
        """
        self._require_started()
        validate_key(pattern, allow_wildcards=True)

        def _on_sample(sample) -> None:
            from zenoh import SampleKind
            alive = sample.kind == SampleKind.PUT
            name = str(sample.key_expr).rsplit("/", 1)[-1]
            try:
                on_change(name, alive)
            except Exception:
                pass

        sub = self._session.liveliness().declare_subscriber(pattern, _on_sample)
        self._tokens.append(sub)
        return sub

    # -- identity --------------------------------------------------------------------

    async def get_identity(self) -> dict[str, Any]:
        return dict(self._identity)

    @property
    def zid(self) -> str:
        """Our Zenoh session id (routing-level identity, not PCM identity)."""
        self._require_started()
        return str(self._session.zid())


__all__ = [
    "ZenohTransport",
    "ZenohTransportConfigError",
    "DEFAULT_TRIBE",
]