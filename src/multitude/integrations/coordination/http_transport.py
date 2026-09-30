# -*- coding: utf-8 -*-
"""PCM coordination over HTTP/JSON — the agents' selected first transport (issue #52).

ADR-001 records the three agents' decision: reachability comes from the existing
private mesh, the message semantics are the signed PCM coordination envelopes, and
the *runtime transport* is an isolated HTTP/JSON endpoint. Zenoh stays supported as
the documented upgrade behind the same seam; this module is the first transport.

Three properties are the reason this file exists, and each is structural rather
than promised:

1. **It is a binding, not a subsystem.** ``HttpJsonTransport`` implements the same
   ``multitude.pcm.transport.Transport`` ABC as ``InMemoryTransport`` and
   ``ZenohTransport``. ``pcm/contact.py`` and ``verify_contact()`` are untouched —
   the protocol does not know which transport carried it.

2. **The route is narrow.** The listener serves exactly one path,
   ``POST /coordination/v1/contact``, and answers with a signed acknowledgement
   produced by the existing ``pcm.contact.contact_handler``. Everything else is a
   404. There is no dispatch table to grow.

3. **Isolation is testable.** This is a *separate server* from
   ``multitude.interfaces.web``. It does not mount, proxy or import that module's
   ``/api/proposals|votes|counsel|memory`` handlers, so a peer that can send a
   coordination envelope cannot reach a service-mutation route through it. Issue
   #52 §3 makes this mandatory, and ``tests/test_coordination_http.py`` asserts it
   instead of documenting it.

What a peer can do here: send a contact and receive an ack. What it cannot do:
execute anything, read PCM state, or mutate a proposal, vote, counsel or memory
record. Reachability is not authorization (``pcm.policy``); an ack is not
authority over the sender.
"""
from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib import error as urllib_error
from urllib import request as urllib_request

from multitude.pcm.transport import (
    QueryableHandler,
    SubscribeHandler,
    Transport,
    TransportError,
    _wildcard_to_regex,
)
from multitude.pcm.namespace import validate_key

#: The single path this listener serves. Deliberately a v1 constant rather than a
#: configurable prefix: one route is the security model, and making it
#: configurable would invite a second one.
COORDINATION_PATH = "/coordination/v1/contact"

#: Header carrying the selector being addressed, so one path can serve any
#: coordinator key without turning into a router.
SELECTOR_HEADER = "X-PCM-Selector"


class HttpJsonTransport(Transport):
    """Transport binding that carries PCM request/response over HTTP/JSON.

    Two roles, chosen by which arguments are given:

    - **listening** (``listen_host``/``listen_port``): serves the single
      coordination route and answers requests whose selector it has registered.
    - **calling** (no listener): sends a request to a peer's coordination URL.

    A node normally does both: it listens so peers can reach it, and calls out so
    it can reach them. The caller supplies the peer URL per request, because in
    this design the address book is the mesh plus ``PCM_PEERS``, which lives
    outside the transport.
    """

    def __init__(
        self,
        identity: dict[str, Any] | None = None,
        *,
        listen_host: str | None = None,
        listen_port: int | None = None,
        on_request: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self._identity = identity or {"pcm_id": "agent:local"}
        self._listen_host = listen_host
        self._listen_port = listen_port
        #: Optional observer called with (selector, payload) for every inbound
        #: request, so a node can log what it was asked without widening the route.
        self._on_request = on_request

        self._subs: list[tuple[Any, str, SubscribeHandler]] = []
        self._queryables: dict[str, QueryableHandler] = {}
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._started = False
        self._loop: asyncio.AbstractEventLoop | None = None

    # -- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        # `port=0` is a valid request for an ephemeral port, so test for None
        # rather than truthiness — `if self._listen_port` silently skipped it.
        if self._listen_host is not None and self._listen_port is not None:
            self._start_listener()
        self._started = True

    async def stop(self) -> None:
        self._started = False
        self._subs.clear()
        self._queryables.clear()
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _start_listener(self) -> None:
        transport = self
        # Narrow once here: the listener is only started when both are set, and
        # mypy/pyright cannot see that across the constructor.
        host = self._listen_host
        port = self._listen_port
        assert host is not None and port is not None

        class Handler(BaseHTTPRequestHandler):
            server_version = "PCMCoordination/1"

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return  # the listener is silent; evidence is the record

            def _send(self, status: int, payload: Any) -> None:
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self) -> None:  # noqa: N802
                # Exactly one route. Anything else 404s: there is no fallthrough
                # to another handler and no route table to extend by accident.
                if self.path != COORDINATION_PATH:
                    self._send(404, {"error": "not found"})
                    return
                selector = self.headers.get(SELECTOR_HEADER)
                if not selector:
                    self._send(400, {"error": f"missing {SELECTOR_HEADER}"})
                    return
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length > 0 else b"{}"
                try:
                    payload = json.loads(raw.decode("utf-8") or "{}")
                except ValueError as exc:
                    self._send(400, {"error": f"invalid JSON body: {exc}"})
                    return
                reply = transport._dispatch(selector, payload)
                if reply is None:
                    # No queryable for that selector, or the handler declined
                    # (contact_handler returns None for unverifiable or
                    # misaddressed contacts — fail closed, no ack, no error detail).
                    self._send(404, {"error": "no queryable for selector"})
                    return
                self._send(200, reply)

        self._server = ThreadingHTTPServer((host, port), Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="pcm-coordination-http", daemon=True
        )
        self._thread.start()

    def _dispatch(self, selector: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Run the registered queryable for ``selector``; None when there is none."""
        handler = self._queryables.get(selector)
        if handler is None:
            return None
        if self._on_request is not None:
            try:
                self._on_request(selector, payload)
            except Exception:
                pass  # an observer must never break the route
        result = handler(payload, selector)
        if asyncio.iscoroutine(result):
            loop = self._loop
            if loop is None:
                raise TransportError("listener dispatched before start()")
            result = asyncio.run_coroutine_threadsafe(result, loop).result(timeout=10)
        if result is None:
            return None
        return result

    # -- Transport interface ------------------------------------------------

    def _require_start(self) -> None:
        if not self._started:
            raise TransportError("transport not started; call start() first")

    async def publish(self, topic: str, event: dict[str, Any]) -> None:
        """Deliver to in-process subscribers.

        This binding is request/response only: issue #52 needs a contact and a
        correlated ack, not pub/sub fan-out. Local subscribers are still served so
        the ABC is honoured and future local wiring works; there is deliberately no
        remote push, because a push channel would be a second exposed surface.
        """
        self._require_start()
        validate_key(topic)
        for regex, _pattern, handler in list(self._subs):
            if regex.match(topic):
                result = handler(event, topic)
                if asyncio.iscoroutine(result):
                    await result

    async def subscribe(self, pattern: str, handler: SubscribeHandler) -> Any:
        self._require_start()
        validate_key(pattern, allow_wildcards=True)
        token = ("httpsub", pattern, len(self._subs))
        self._subs.append((_wildcard_to_regex(pattern), pattern, handler))
        return token

    async def request(
        self,
        selector: str,
        payload: dict[str, Any] | None = None,
        timeout: float = 5.0,
        *,
        peer_url: str | None = None,
    ) -> list[dict[str, Any]]:
        """POST ``payload`` to the peer's coordination route and return replies.

        ``peer_url`` is the peer's base URL (the mesh address it binds). It is a
        per-call argument rather than transport state because addressing belongs to
        the deployment, not to the protocol binding.
        """
        self._require_start()
        validate_key(selector, allow_wildcards=True)
        if not peer_url:
            raise TransportError(
                "request() needs peer_url: the HTTP binding does not discover peers "
                "(reachability is the mesh's job, per ADR-001)"
            )
        url = peer_url.rstrip("/") + COORDINATION_PATH
        body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
        req = urllib_request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                SELECTOR_HEADER: selector,
            },
        )
        try:
            with urllib_request.urlopen(req, timeout=timeout) as resp:
                reply = json.loads(resp.read().decode("utf-8"))
        except urllib_error.HTTPError as exc:
            if exc.code == 404:
                # No queryable, or the peer declined to acknowledge. Both mean
                # "not a contact" — return no replies so contact_peer raises.
                return []
            raise TransportError(f"coordination request failed: HTTP {exc.code}") from exc
        except (urllib_error.URLError, TimeoutError, ValueError) as exc:
            raise TransportError(f"coordination request failed: {exc}") from exc
        return [reply] if isinstance(reply, dict) else []

    async def register_queryable(self, selector: str, handler: QueryableHandler) -> Any:
        self._require_start()
        validate_key(selector)
        self._queryables[selector] = handler
        return ("httpq", selector)

    async def get_identity(self) -> dict[str, Any]:
        return dict(self._identity)

    # -- introspection ------------------------------------------------------

    @property
    def bound_address(self) -> tuple[str, int] | None:
        """The address actually bound (useful when port 0 was requested)."""
        if self._server is None:
            return None
        host, port = self._server.server_address[:2]
        return (str(host), int(port))


__all__ = ["HttpJsonTransport", "COORDINATION_PATH", "SELECTOR_HEADER"]
