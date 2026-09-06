# -*- coding: utf-8 -*-
"""Unit tests — PCM fabric layer (migration spec §29 unit criteria).

Covers: namespace generation/validation, PCM events, serialization,
payload validation, permission policy, and the generic Transport
abstraction (InMemoryTransport with Zenoh wildcard semantics).

Run: python3 tests/test_pcm_fabric.py  (or via pytest)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.integrations.zenoh.fabric import ZenohTransport
from multitude.pcm.events import (EventError, PcmEvent, PcmIdentity,
                                  create_event, validate_payload)
from multitude.pcm.namespace import (DOMAINS, KeyError_, agent_message_key,
                                     conversation_key, key, parse_key,
                                     pattern, query_key, task_key,
                                     validate_key)
from multitude.pcm.policy import Decision, Policy, PolicyDenied
from multitude.pcm.transport import (InMemoryTransport, TransportError,
                                     _wildcard_to_regex)


def test_namespace() -> int:
    failures: list[str] = []
    # concrete keys
    k = agent_message_key("hermes")
    if k != "pcm/agent/hermes/message":
        failures.append(f"agent_message_key wrong: {k}")
    if parse_key(k) != {"domain": "agent", "entity": "hermes", "resource": "message"}:
        failures.append(f"parse_key wrong: {parse_key(k)}")
    if conversation_key("abc123") != "pcm/conversation/abc123/message":
        failures.append("conversation_key wrong")
    if task_key("123", "result") != "pcm/task/123/result":
        failures.append("task_key wrong")
    if query_key("agent", "hermes") != "pcm/query/agent/hermes":
        failures.append("query_key wrong")
    # patterns with wildcards
    p = pattern("agent", "*", "message")
    if p != "pcm/agent/*/message":
        failures.append(f"pattern wrong: {p}")
    p2 = pattern("home", "**", "temperature")
    if p2 != "pcm/home/**/temperature":
        failures.append(f"double-wildcard pattern wrong: {p2}")
    # validation failures
    for bad in ("other/agent/x/y", "pcm", "pcm/agent", "pcm/age nt/x/y",
                "pcm/agent//message"):
        try:
            validate_key(bad)
            failures.append(f"invalid key accepted: {bad!r}")
        except KeyError_:
            pass
    # wildcards not allowed in published keys
    try:
        key("agent", "*", "message")
        failures.append("wildcard accepted in published key")
    except KeyError_:
        pass
    # domain vocabulary is closed and machine-readable
    if "agent" not in DOMAINS or len(DOMAINS) < 14:
        failures.append("domain vocabulary wrong")
    print("[namespace] build/parse/validate OK")
    return len(failures)


def test_events() -> int:
    failures: list[str] = []
    ev = create_event(
        "pcm.message", "agent:alice", "pcm/agent/alice/message",
        {"text": "hello fabric"},
    )
    d = ev.model_dump()
    if d["version"] != 1 or d["type"] != "pcm.message":
        failures.append(f"event shape wrong: {d}")
    # round trip serialization
    rev = PcmEvent.from_json(ev.to_json())
    if rev.payload != {"text": "hello fabric"} or rev.author != "agent:alice":
        failures.append("event JSON round trip wrong")
    # unknown type rejected
    try:
        create_event("matrix.room.message", "agent:alice", "pcm/agent/alice/message")
        failures.append("matrix-typed event accepted")
    except EventError:
        pass
    # author shape enforced
    try:
        create_event("pcm.message", "alice", "pcm/agent/alice/message")
        failures.append("kindless author accepted")
    except EventError:
        pass
    # identity kinds
    ident = PcmIdentity.parse("human:alice")
    if ident.pcm_id != "human:alice":
        failures.append("identity parse wrong")
    try:
        PcmIdentity.check(kind="alien", name="x")
        failures.append("unknown identity kind accepted")
    except EventError:
        pass
    # per-type payload validation
    try:
        validate_payload("pcm.device.command", {"action": "light.set"})
        failures.append("command without target accepted")
    except EventError:
        pass
    try:
        validate_payload("pcm.resource", {"hash": "h", "mime": "image/jpeg"})
        failures.append("resource without location accepted")
    except EventError:
        pass
    print("[events] create/serialize/validate OK")
    return len(failures)


def test_policy() -> int:
    failures: list[str] = []
    p = Policy()
    p.allow("light.*", "device:*", authors=("agent:hermes",),
            parameter_limits={"brightness": (0, 100)}, max_per_minute=5)
    # allowed
    if p.decide("agent:hermes", "light.set", "device:lamp01",
                {"brightness": 40}) is not Decision.ALLOW:
        failures.append("allowed action denied")
    # default deny for others
    if p.decide("agent:mallory", "light.set", "device:lamp01") is not Decision.DENY:
        failures.append("unlisted author allowed")
    if p.decide("agent:hermes", "door.unlock", "device:door01") is not Decision.DENY:
        failures.append("unlisted action allowed")
    # parameter range enforced
    if p.decide("agent:hermes", "light.set", "device:lamp01",
                {"brightness": 101}) is not Decision.DENY:
        failures.append("out-of-range parameter allowed")
    # authorize raises
    try:
        p.authorize("agent:mallory", "light.set", "device:lamp01")
        failures.append("authorize did not raise for denied action")
    except PolicyDenied:
        pass
    # high-risk actions need explicit rules even under an allow-all policy
    open_policy = Policy(default=Decision.ALLOW)
    try:
        open_policy.authorize("agent:x", "drone.arm", "drone:01")
        failures.append("high-risk action sailed through open policy")
    except PolicyDenied:
        pass
    # A rule for one author must not open the explicit high-risk gate to
    # everyone else when the fallback policy is ALLOW.
    open_policy.allow("power.set", "device:lamp", authors=("human:alice",))
    try:
        open_policy.authorize("agent:mallory", "power.set", "device:lamp")
        failures.append("another author's explicit high-risk rule was reused")
    except PolicyDenied:
        pass
    # explicit high-risk rule works
    p.allow("drone.arm", "drone:01", authors=("human:alice",))
    p.authorize("human:alice", "drone.arm", "drone:01")
    # rate limit: 5/min — the 6th must fail
    for i in range(5):
        p.authorize("agent:hermes", "light.set", "device:lamp01", {"brightness": 10})
    try:
        p.authorize("agent:hermes", "light.set", "device:lamp01", {"brightness": 10})
        failures.append("rate limit not enforced")
    except PolicyDenied:
        pass
    # Rate limits belonging to another author must not throttle Alice.
    scoped_limits = Policy()
    scoped_limits.allow("light.set", "device:*", authors=("alice",), max_per_minute=100)
    scoped_limits.allow("light.set", "device:*", authors=("bob",), max_per_minute=1)
    try:
        scoped_limits.authorize("alice", "light.set", "device:lamp")
        scoped_limits.authorize("alice", "light.set", "device:lamp")
    except PolicyDenied as exc:
        failures.append(f"another author's rate limit affected Alice: {exc}")
    print("[policy] allow/deny/ranges/high-risk/rate-limit OK")
    return len(failures)


def test_transport_abstraction() -> int:
    failures: list[str] = []

    async def run() -> list[str]:
        out: list[str] = []
        t = InMemoryTransport({"pcm_id": "agent:test"})
        await t.start()
        got: list[tuple[dict, str]] = []

        def handler(event: dict, topic: str) -> None:
            got.append((event, topic))

        await t.subscribe("pcm/device/*/telemetry", handler)
        await t.publish("pcm/device/drone01/telemetry", {"alt": 120})
        # no wildcard bleed
        await t.publish("pcm/agent/hermes/message", {"text": "not telemetry"})
        if len(got) != 1 or got[0][0] != {"alt": 120}:
            failures.append(f"pubsub wrong: {got}")
        # ** matches nested
        got2: list[str] = []
        await t.subscribe("pcm/home/**/temperature",
                          lambda e, k: got2.append(k))
        await t.publish("pcm/home/kitchen/sensors/temperature", {"c": 21.5})
        if got2 != ["pcm/home/kitchen/sensors/temperature"]:
            failures.append(f"** wildcard wrong: {got2}")
        # queryable round trip
        await t.register_queryable(
            "pcm/query/agent/hermes",
            lambda req, k: {"answer": 42, "req": req})
        replies = await t.request("pcm/query/agent/hermes", {"q": "life"})
        if len(replies) != 1 or replies[0]["answer"] != 42:
            failures.append(f"request wrong: {replies}")
        # identity
        ident = await t.get_identity()
        if ident["pcm_id"] != "agent:test":
            failures.append(f"identity wrong: {ident}")
        # not-started transport refuses
        t2 = InMemoryTransport()
        try:
            await t2.publish("pcm/agent/x/message", {})
            failures.append("unstarted transport accepted publish")
        except TransportError:
            pass
        await t.stop()
        out.append("done")
        return out

    asyncio.run(run())
    print("[transport] pubsub/wildcards/queryable/identity/guard OK")
    return len(failures)


def test_zenoh_transport_shapes() -> int:
    """ZenohTransport object shape without opening a session (no deps needed
    beyond import; real sessions are integration-tested separately)."""
    failures: list[str] = []
    t = ZenohTransport({"pcm_id": "agent:shape"})
    if not isinstance(t, object):
        failures.append("not an object")
    # interface conformance: all generic methods exist
    for m in ("start", "stop", "publish", "subscribe", "request",
              "register_queryable", "get_identity"):
        if not callable(getattr(t, m, None)):
            failures.append(f"ZenohTransport missing {m}")
    # env config parse: PCM_ZENOH_CONNECT switches to client mode
    import os
    saved = os.environ.get("PCM_ZENOH_CONNECT")
    try:
        os.environ["PCM_ZENOH_CONNECT"] = "tcp/localhost:7447"
        t2 = ZenohTransport()
        if t2._mode != "client":
            failures.append("env connect did not switch mode")
    finally:
        if saved is None:
            os.environ.pop("PCM_ZENOH_CONNECT", None)
        else:
            os.environ["PCM_ZENOH_CONNECT"] = saved
    print("[zenoh-shape] interface + env config OK")
    return len(failures)


def main() -> int:
    total = (test_namespace() + test_events() + test_policy()
             + test_transport_abstraction() + test_zenoh_transport_shapes())
    print()
    if total:
        print(f"{total} FAILURES")
        return 1
    print("ALL PCM FABRIC UNIT TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# pytest wrappers (canonical suite collects these)
def test_pcm_fabric_namespace():
    assert test_namespace() == 0

def test_pcm_fabric_events():
    assert test_events() == 0

def test_pcm_fabric_policy():
    assert test_policy() == 0

def test_pcm_fabric_transport():
    assert test_transport_abstraction() == 0

def test_pcm_fabric_zenoh_shape():
    assert test_zenoh_transport_shapes() == 0