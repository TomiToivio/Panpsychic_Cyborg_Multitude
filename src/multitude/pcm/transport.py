# -*- coding: utf-8 -*-
"""PCM transport abstraction — the fabric seam (spec §3).

PCM Core must not depend on Zenoh-specific implementation details. This
module defines the generic asynchronous transport interface the
application layer (MultitudeService, adapters, demos) programs against.
Concrete implementations:

- :class:`multitude.integrations.zenoh.fabric.ZenohTransport` — Zenoh
  peer-to-peer fabric (pub/sub, queryables, liveliness).
- :class:`InMemoryTransport` — loopback implementation for unit tests
  and offline development; same semantics, no network.

Interface (the migration contract, verbatim)::

    class Transport:
        async def start(self): ...
        async def stop(self): ...
        async def publish(self, topic, event): ...
        async def subscribe(self, pattern, handler): ...
        async def request(self, selector, payload=None): ...
        async def register_queryable(self, selector, handler): ...
        async def get_identity(self): ...

Conventions:
- ``topic``/``pattern``/``selector`` are PCM key expressions
  (namespace.py); wildcards are valid only in patterns/selectors.
- ``event``/``payload`` are JSON-serializable dicts (events.py).
- ``handler`` is a callable ``(payload: dict, topic: str) -> None`` for
  subscriptions, and ``(payload: dict | None, topic: str) -> dict`` for
  queryables (the return value is the reply).
- ``request`` returns a list of reply dicts (multiple queryables may
  answer a selector).
- Implementations must never raise from background callbacks; delivery
  errors surface to the caller of publish/request instead.
"""
from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable

from multitude.pcm.namespace import PCM_KEY_PREFIX, validate_key

SubscribeHandler = Callable[[dict[str, Any], str], Any]
QueryableHandler = Callable[[dict[str, Any] | None, str], dict[str, Any]]


class TransportError(RuntimeError):
    """Transport misuse or failure."""


class Transport(ABC):
    """Generic transport interface. See module docstring."""

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def publish(self, topic: str, event: dict[str, Any]) -> None: ...

    @abstractmethod
    async def subscribe(self, pattern: str,
                        handler: SubscribeHandler) -> Any: ...

    @abstractmethod
    async def request(self, selector: str,
                      payload: dict[str, Any] | None = None,
                      timeout: float = 5.0) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def register_queryable(self, selector: str,
                                 handler: QueryableHandler) -> Any: ...

    @abstractmethod
    async def get_identity(self) -> dict[str, Any]: ...


def _wildcard_to_regex(pattern_: str) -> re.Pattern:
    """Compile a PCM pattern (``*`` one segment, ``**`` any) to a regex.

    Zenoh semantics: ``*`` matches exactly one segment; ``**`` matches
    zero or more segments. ``fnmatch``-style matching happens per key.
    """
    parts = pattern_.split("/")
    # parts[0] is the fixed "pcm" prefix; emit it once.
    out = ["^" + re.escape(PCM_KEY_PREFIX)]
    for part in parts[1:]:
        if part == "**":
            out.append("(?:/[A-Za-z0-9_.\\-]+)*")
        elif part == "*":
            out.append("/[A-Za-z0-9_.\\-]+")
        else:
            out.append("/" + re.escape(part))
    return re.compile("".join(out) + "$")


class InMemoryTransport(Transport):
    """Loopback transport with Zenoh-matching wildcard semantics.

    Everything happens inside one process; used by unit tests and as the
    graceful-offline development mode.
    """

    def __init__(self, identity: dict[str, Any] | None = None) -> None:
        self._identity = identity or {"pcm_id": "agent:local"}
        self._subs: list[tuple[re.Pattern, str, SubscribeHandler]] = []
        self._queryables: dict[str, tuple[str, QueryableHandler]] = {}
        self._started = False

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False
        self._subs.clear()
        self._queryables.clear()

    def _require_start(self) -> None:
        if not self._started:
            raise TransportError("transport not started; call start() first")

    async def publish(self, topic: str, event: dict[str, Any]) -> None:
        self._require_start()
        validate_key(topic)
        for regex, pat, handler in list(self._subs):
            if regex.match(topic):
                result = handler(event, topic)
                if asyncio.iscoroutine(result):
                    await result

    async def subscribe(self, pattern: str, handler: SubscribeHandler) -> Any:
        self._require_start()
        validate_key(pattern, allow_wildcards=True)
        regex = _wildcard_to_regex(pattern)
        token = ("memsub", pattern, len(self._subs))
        self._subs.append((regex, pattern, handler))
        return token

    async def register_queryable(self, selector: str,
                                 handler: QueryableHandler) -> Any:
        self._require_start()
        validate_key(selector)
        self._queryables[selector] = (selector, handler)
        return ("memq", selector)

    async def request(self, selector: str,
                      payload: dict[str, Any] | None = None,
                      timeout: float = 5.0) -> list[dict[str, Any]]:
        self._require_start()
        validate_key(selector, allow_wildcards=True)
        regex = _wildcard_to_regex(selector)
        replies: list[dict[str, Any]] = []
        for key_, (_, handler) in list(self._queryables.items()):
            if regex.match(key_):
                result = handler(payload, key_)
                if asyncio.iscoroutine(result):
                    result = await result
                if result is not None:
                    replies.append(result)
        return replies

    async def get_identity(self) -> dict[str, Any]:
        return dict(self._identity)


__all__ = [
    "Transport",
    "TransportError",
    "InMemoryTransport",
    "SubscribeHandler",
    "QueryableHandler",
]