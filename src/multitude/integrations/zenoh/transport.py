# -*- coding: utf-8 -*-
"""Zenoh transport — Phase 2 PCM node-to-node envelope exchange.

Replaces the Matrix room as the primary peer transport for Phase 2
(maintainer decision 2026-09-05: zenoh replaces Matrix). NETWORKING_STACK.md
§7 Phase 2 changes transport; the MVP criterion is unchanged:

    Two PCM nodes exchange signed envelopes, and both can rebuild
    identical tribe state from their own event logs. No third party.

Why zenoh fits PCM (and why Matrix was the wrong shape for it):

  - Peer-native: nodes talk directly (peer-to-peer scouting over UDP
    multicast on the LAN, or via a router for WAN). No homeserver, no
    third party — the acceptance criterion "no third party involved"
    becomes architectural instead of aspirational.
  - No account infrastructure: no registration, no homeserver database,
    no Postgres. A node is a process, not a user on someone's server.
  - Pub/sub + queryables: envelope broadcast (tribe square) is a plain
    keyed subscription; peer request/response (DM-like counsel) is a
    zenoh query — both primitives the PCM protocol needs.
  - Liveliness tokens: node presence (did:key online) is a first-class
    primitive, not a Matrix presence hack.
  - Python binding maintained (eclipse-zenoh 1.10, 2026), Rust core.

Key layout (all under the pcm/ prefix so unrelated zenoh traffic never
sees PCM):

    pcm/v1/square/<tribe_id>       — the tribe square (every node's
                                     signed envelopes, broadcast)
    pcm/v1/direct/<from>/<to>      — pairwise peer channel (DMs)
    pcm/v1/liveliness/<tribe>/<did> — node presence (liveliness token)

Envelope flow:

  outbound  Envelope.create -> sign(identity key) -> canonical JSON ->
            session.put("pcm/v1/square/<tribe>", payload)
  inbound   subscriber -> Envelope.model_validate -> envelope.verify()
            -> handler(trusts verified from_did) -> tribe/service layer

Verification happens BEFORE any handler sees the message — a bad
signature is dropped at the transport edge, exactly as the spec's rule
2 requires ("receivers verify before trusting from").

Dormancy guard (same pattern as the Matrix skeleton): the transport
refuses to run without PCM_ZENOH_ENABLED=true. Credentials: none needed
for peer mode on the LAN; router endpoints come from PCM_ZENOH_CONNECT
(comma-separated locator list, e.g. tcp/zenoh.example.net:7447) —
environment only, never in Git.

Dependencies: eclipse-zenoh (optional extra: `pcm-zenoh`). Import is
lazy so the rest of PCM works without it installed.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

PCM_KEY_PREFIX = "pcm/v1"
DEFAULT_TRIBE = "default"


class ZenohConfigError(RuntimeError):
    """Zenoh transport is not configured or is disabled."""


def square_key(tribe_id: str = DEFAULT_TRIBE) -> str:
    """Key expression for a tribe square (broadcast channel)."""
    safe = tribe_id.replace("*", "").replace("?", "").strip("/")
    return f"{PCM_KEY_PREFIX}/square/{safe}"


def direct_key(from_did: str, to_did: str) -> str:
    """Pairwise channel key; direction matters only for key readability."""
    def short(did: str) -> str:
        return did.rsplit(":", 1)[-1][:16]
    return f"{PCM_KEY_PREFIX}/direct/{short(from_did)}/{short(to_did)}"


@dataclass
class ZenohTransportConfig:
    """All configuration comes from the environment or explicit kwargs."""

    tribe_id: str = DEFAULT_TRIBE
    # peer (LAN multicast scouting) or router (via PCM_ZENOH_CONNECT)
    mode: str = "peer"
    connect_endpoints: list[str] = field(default_factory=list)
    listen_endpoints: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls, tribe_id: str = DEFAULT_TRIBE) -> "ZenohTransportConfig":
        connect = [e for e in os.environ.get("PCM_ZENOH_CONNECT", "").split(",") if e.strip()]
        listen = [e for e in os.environ.get("PCM_ZENOH_LISTEN", "").split(",") if e.strip()]
        mode = "router" if connect else "peer"
        return cls(tribe_id=tribe_id, mode=mode,
                   connect_endpoints=connect, listen_endpoints=listen)


@dataclass
class ZenohTransport:
    """One PCM node's zenoh session: publish + receive signed envelopes.

    ``on_envelope`` handlers run only for VERIFIED envelopes; the
    verified dict (by_alias shape: from/to keys) is handed over. A node
    drops its own loops (same envelope id seen twice) silently.
    """

    tribe: Any                        # tribe or service layer; the handler decides
    member_name: str
    on_envelope: Optional[Callable[[dict[str, Any]], None]] = None
    config: ZenohTransportConfig = field(default_factory=ZenohTransportConfig)
    _session: Any = None
    _subscriber: Any = None
    _liveliness: Any = None
    _seen: set = field(default_factory=set)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    # -- lifecycle ----------------------------------------------------------

    def _guard(self) -> None:
        if os.environ.get("PCM_ZENOH_ENABLED", "").lower() not in {"1", "true", "yes", "on"}:
            raise ZenohConfigError(
                "zenoh transport is dormant; set PCM_ZENOH_ENABLED=true to enable it.")

    def _build_config(self):
        import zenoh
        cfg = zenoh.Config()
        if self.config.mode == "router" and self.config.connect_endpoints:
            cfg.insert_json5("mode", json.dumps("client"))
            cfg.insert_json5("connect/endpoints",
                             json.dumps(self.config.connect_endpoints))
        elif self.config.listen_endpoints:
            cfg.insert_json5("listen/endpoints/peer",
                             json.dumps(self.config.listen_endpoints))
        return cfg

    def start(self) -> None:
        """Open the session, subscribe the tribe square, declare presence."""
        self._guard()
        import zenoh
        self._session = zenoh.open(self._build_config())
        key = square_key(self.config.tribe_id)
        self._subscriber = self._session.declare_subscriber(
            key, self._on_sample)
        # presence: liveliness token keyed by tribe + our short DID
        did = getattr(self.tribe, "did", "") or self.member_name
        try:
            self._liveliness = self._session.liveliness().declare_token(
                f"{PCM_KEY_PREFIX}/liveliness/{self.config.tribe_id}/{did[:24]}")
        except Exception:  # liveliness is optional nicety, not load-bearing
            self._liveliness = None

    def close(self) -> None:
        for attr in ("_liveliness", "_subscriber", "_session"):
            obj = getattr(self, attr, None)
            if obj is not None:
                try:
                    obj.undeclare() if attr != "_session" else obj.close()
                except Exception:
                    pass
                setattr(self, attr, None)

    # -- publish ------------------------------------------------------------

    def publish_envelope(self, envelope_dict: dict[str, Any],
                         *, key: Optional[str] = None) -> str:
        """Publish one signed envelope (already verified-signed by caller).

        ``envelope_dict`` is the by-alias dump of pcm.envelope.Envelope.
        Returns the zenoh key used.
        """
        self._guard()
        if self._session is None:
            raise ZenohConfigError("transport not started; call start() first")
        payload = json.dumps(envelope_dict, ensure_ascii=False).encode("utf-8")
        key = key or square_key(self.config.tribe_id)
        self._session.put(key, payload)
        return key

    def query_peer(self, target_did: str, envelope_dict: dict[str, Any],
                   timeout_ms: int = 3000) -> list[dict[str, Any]]:
        """Peer-to-peer query: send a signed envelope, collect verified replies.

        The reply handler verifies each reply envelope before it enters
        the result list — same edge-verification as the subscriber path.
        """
        import zenoh
        if self._session is None:
            raise ZenohConfigError("transport not started; call start() first")
        selector = f"{direct_key(self.member_name, target_did)}"
        replies: list[dict[str, Any]] = []
        for reply in self._session.get(selector,
                                       payload=json.dumps(envelope_dict).encode(),
                                       timeout=timeout_ms / 1000.0):
            try:
                data = json.loads(reply.ok.payload.to_bytes())
                env = _verify_or_raise(data)
                replies.append(env)
            except Exception:
                continue  # unverifiable replies never surface
        return replies

    def declare_queryable(self, handler: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        """Answer peer queries on our direct key. Handler receives a
        verified inbound envelope dict, returns a (signed) envelope dict."""
        if self._session is None:
            raise ZenohConfigError("transport not started; call start() first")
        key = direct_key("*", self.member_name)

        def _answer(query):
            try:
                inbound = json.loads(query.payload.to_bytes())
                env = _verify_or_raise(inbound)
                answer = handler(env)
                if answer:
                    query.reply(query.key_expr,
                                json.dumps(answer, ensure_ascii=False).encode())
            except Exception:
                pass  # unverified or malformed queries get silence
        self._session.declare_queryable(key, _answer)

    # -- receive ------------------------------------------------------------

    def _on_sample(self, sample) -> None:
        """Zenoh subscriber callback: verify first, then dispatch."""
        try:
            data = json.loads(sample.payload.to_bytes())
        except Exception:
            return
        try:
            env = _verify_or_raise(data)
        except Exception:
            return  # rule 2: unverified envelopes die at the edge
        # Drop our own publications (both nodes sit on the same square key).
        my_did = getattr(self.tribe, "did", "")
        if my_did and env.get("from") == my_did:
            return
        with self._lock:
            env_id = env.get("id", "")
            if env_id and env_id in self._seen:
                return
            self._seen.add(env_id)
        handler = self.on_envelope or self._default_handler
        if handler is not None:
            try:
                handler(env)
            except Exception:
                pass

    def _default_handler(self, env: dict[str, Any]) -> None:
        """Default dispatch: write to the tribe log via the service layer."""
        content = env.get("content", {}) or {}
        text = content.get("text") or content.get("message") or ""
        if text and hasattr(self.tribe, "say"):
            self.tribe.say(str(text), kind="say", meta={
                "interface": "zenoh",
                "from_did": env.get("from"),
                "envelope_id": env.get("id"),
                "envelope_type": env.get("type"),
            })


def _verify_or_raise(data: dict[str, Any]) -> dict[str, Any]:
    """Verify an inbound envelope dict. Raises on ANY problem."""
    from multitude.pcm.envelope import Envelope
    env = Envelope.model_validate(data)
    env.verify()
    return env.model_dump(by_alias=True)


def start_transport(tribe: Any, member_name: str,
                    identity: dict[str, Any], private_key: Any,
                    config: ZenohTransportConfig | None = None,
                    on_envelope: Callable[[dict[str, Any]], None] | None = None
                    ) -> ZenohTransport:
    """Convenience bootstrap: build, sign-check, and start a transport.

    ``identity`` is pcm.identity.load_identity output; ``private_key``
    its Ed25519 private key. The transport itself never signs — callers
    sign envelopes with the identity key before publishing; the private
    key is only checked once here so a miswired node fails fast.
    """
    from multitude.pcm.identity import did_from_pubkey, private_key_from_identity
    did = identity["did"]
    actual = did_from_pubkey(_pub_raw(private_key))
    if actual != did:
        raise ZenohConfigError(f"identity/did mismatch: key is {actual}, claimed {did}")
    transport = ZenohTransport(tribe=tribe, member_name=member_name,
                               on_envelope=on_envelope,
                               config=config or ZenohTransportConfig.from_env())
    transport.start()
    return transport


def _pub_raw(private_key) -> bytes:
    from cryptography.hazmat.primitives import serialization
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)