# -*- coding: utf-8 -*-
"""Integration tests — real Zenoh sessions (migration spec §29 integration).

Requires the optional extra:  pip install eclipse-zenoh
Covers: publish/subscribe across sessions, queryables, liveliness
presence, wildcard subscriptions, multiple peers, reconnects, and
router/client topology when a zenohd router binary is available.

Run: python3 tests/test_pcm_fabric_integration.py
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.integrations.zenoh.fabric import ZenohTransport
from multitude.pcm.events import create_event


def _zenoh_available() -> bool:
    try:
        import zenoh  # noqa: F401
        return True
    except ImportError:
        return False


def _find_router() -> str | None:
    """Locate a zenohd binary (PATH or common install dirs)."""
    for name in ("zenohd", "zenoh-routerd"):
        path = shutil.which(name)
        if path:
            return path
    return None


async def scenario_pubsub() -> list[str]:
    """Test: agent receives what a sensor publishes, live, cross-session."""
    out: list[str] = []
    a = ZenohTransport({"pcm_id": "agent:hermes"})
    s = ZenohTransport({"pcm_id": "sensor:room1"})
    await a.start()
    await s.start()
    got: list[tuple[dict, str]] = []
    await a.subscribe("pcm/sensor/*/temperature", lambda e, k: got.append((e, k)))
    await asyncio.sleep(0.5)  # scouting settle
    ev = create_event("pcm.sensor.reading", "sensor:room1",
                      "pcm/sensor/room1/temperature", {"value": 22.5, "unit": "C"})
    await s.publish("pcm/sensor/room1/temperature", ev.model_dump())
    for _ in range(20):
        await asyncio.sleep(0.2)
        if got:
            break
    assert got, "agent never received the sensor reading"
    event, topic = got[0]
    assert event["payload"]["value"] == 22.5
    assert topic == "pcm/sensor/room1/temperature"
    out.append("[pubsub] sensor -> agent reading delivered cross-session")
    await a.stop()
    await s.stop()
    return out


async def scenario_queryable() -> list[str]:
    """Test: human asks; agent queryable answers; request returns replies."""
    out: list[str] = []
    agent = ZenohTransport({"pcm_id": "agent:hermes"})
    human = ZenohTransport({"pcm_id": "human:USER"})
    await agent.start()
    await human.start()

    async def answer(request, topic):
        return {"answer": "22.5 C", "request": request}

    await agent.register_queryable("pcm/query/agent/hermes", answer)
    await asyncio.sleep(0.5)
    replies = await human.request("pcm/query/agent/hermes",
                                  {"question": "temperature?"}, timeout=5.0)
    assert replies, "query got no replies"
    assert replies[0]["answer"] == "22.5 C"
    out.append("[queryable] request -> reply round trip OK")
    await agent.stop()
    await human.stop()
    return out


async def scenario_liveliness() -> list[str]:
    """Test: node presence via Zenoh liveliness (token declare + drop)."""
    out: list[str] = []
    watcher = ZenohTransport({"pcm_id": "agent:watcher"})
    drone = ZenohTransport({"pcm_id": "drone:01"})
    await watcher.start()
    events: list[tuple[str, bool]] = []
    await watcher.watch_liveliness("pcm/liveliness/**",
                                   lambda name, alive: events.append((name, alive)))
    await drone.start()
    for _ in range(30):
        await asyncio.sleep(0.2)
        if any(n == "01" and a for n, a in events):
            break
    assert any(n == "01" and a for n, a in events), \
        f"liveliness alive event never fired: {events}"
    # stop the drone -> token dropped -> gone event
    await drone.stop()
    gone = False
    for _ in range(50):
        await asyncio.sleep(0.2)
        if any(n == "01" and not a for n, a in events):
            gone = True
            break
    assert gone, f"liveliness gone event never fired: {events}"
    out.append("[liveliness] alive + gone presence semantics OK")
    await watcher.stop()
    return out


async def scenario_wildcards() -> list[str]:
    """Test: three peers; wildcard subscription catches entity variants."""
    out: list[str] = []
    a = ZenohTransport({"pcm_id": "agent:a"})
    b = ZenohTransport({"pcm_id": "agent:b"})
    dev = ZenohTransport({"pcm_id": "device:lamp01"})
    for t in (a, b, dev):
        await t.start()
    await asyncio.sleep(0.5)
    got_a: list[str] = []
    got_b: list[str] = []
    await a.subscribe("pcm/device/*/state", lambda e, k: got_a.append(k))
    await b.subscribe("pcm/device/lamp01/*", lambda e, k: got_b.append(k))
    await asyncio.sleep(0.3)
    await dev.publish("pcm/device/lamp01/state", {"on": True})
    for _ in range(30):
        await asyncio.sleep(0.2)
        if got_a and got_b:
            break
    assert got_a == ["pcm/device/lamp01/state"], f"a: {got_a}"
    assert got_b == ["pcm/device/lamp01/state"], f"b: {got_b}"
    out.append("[wildcards] two peers both matched their patterns")
    for t in (a, b, dev):
        await t.stop()
    return out


async def scenario_reconnect() -> list[str]:
    """Test 4: disconnect a node, reconnect, communication resumes."""
    out: list[str] = []
    a = ZenohTransport({"pcm_id": "agent:hermes"})
    s = ZenohTransport({"pcm_id": "sensor:room1"})
    await a.start()
    await s.start()
    got: list[int] = []
    await a.subscribe("pcm/sensor/room1/temperature", lambda e, k: got.append(1))
    await asyncio.sleep(0.5)
    await s.publish("pcm/sensor/room1/temperature", {"value": 20.0})
    for _ in range(30):
        await asyncio.sleep(0.2)
        if got:
            break
    assert got, "first phase got nothing"
    # disconnect the sensor
    await s.stop()
    await asyncio.sleep(0.5)
    # reconnect a fresh sensor session with the same identity
    s2 = ZenohTransport({"pcm_id": "sensor:room1"})
    await s2.start()
    await asyncio.sleep(0.7)
    await s2.publish("pcm/sensor/room1/temperature", {"value": 21.0})
    count_before = len(got)
    for _ in range(40):
        await asyncio.sleep(0.2)
        if len(got) > count_before:
            break
    assert len(got) > count_before, "communication did not resume after reconnect"
    out.append("[reconnect] node restarted and traffic resumed cleanly")
    await a.stop()
    await s2.stop()
    return out


async def scenario_router(router_bin: str) -> list[str]:
    """Test: two client sessions bridge through a zenohd router."""
    out: list[str] = []
    workdir = tempfile.mkdtemp(prefix="pcm-zenoh-router-")
    cfg = os.path.join(workdir, "router.json5")
    with open(cfg, "w", encoding="utf-8") as fh:
        fh.write('{"mode":"router","listen":{"endpoints":{"router":["tcp/127.0.0.1:17447"]}}}')
    proc = subprocess.Popen([router_bin, "-c", cfg],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 10
        ready = False
        while time.time() < deadline:
            time.sleep(0.3)
            # router ready when the port accepts connections
            import socket
            with socket.socket() as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", 17447)) == 0:
                    ready = True
                    break
        assert ready, "router never came up"
        c1 = ZenohTransport({"pcm_id": "agent:x1"}, mode="client",
                            connect_endpoints=["tcp/127.0.0.1:17447"])
        c2 = ZenohTransport({"pcm_id": "agent:b"}, mode="client",
                            connect_endpoints=["tcp/127.0.0.1:17447"])
        await c1.start()
        await c2.start()
        got: list[dict] = []
        await c2.subscribe("pcm/agent/*/message", lambda e, k: got.append(e))
        await asyncio.sleep(0.7)
        await c1.publish("pcm/agent/b/message", {"text": "via router"})
        for _ in range(30):
            await asyncio.sleep(0.2)
            if got:
                break
        assert got, "router-bridged message never arrived"
        out.append("[router] client sessions bridged through zenohd OK")
        await c1.stop()
        await c2.stop()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    return out


def main() -> int:
    if not _zenoh_available():
        print("eclipse-zenoh not installed — skipping integration tests")
        return 0
    failures: list[str] = []

    def run(coro):
        try:
            for line in asyncio.run(coro):
                print(line)
        except AssertionError as e:
            failures.append(str(e))
        except Exception as e:
            failures.append(f"{type(e).__name__}: {e}")

    run(scenario_pubsub())
    run(scenario_queryable())
    run(scenario_liveliness())
    run(scenario_wildcards())
    run(scenario_reconnect())
    router = _find_router()
    if router:
        run(scenario_router(router))
    else:
        print("[router] zenohd binary not available — router test skipped")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("ALL PCM FABRIC INTEGRATION TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# pytest wrappers (canonical suite collects these; skipped without the dep)
import pytest  # noqa: E402

_zenoh = pytest.mark.skipif(not _zenoh_available(), reason="eclipse-zenoh not installed")

@_zenoh
def test_fabric_pubsub():
    asyncio.run(scenario_pubsub())

@_zenoh
def test_fabric_queryable():
    asyncio.run(scenario_queryable())

@_zenoh
def test_fabric_liveliness():
    asyncio.run(scenario_liveliness())

@_zenoh
def test_fabric_wildcards():
    asyncio.run(scenario_wildcards())

@_zenoh
def test_fabric_reconnect():
    asyncio.run(scenario_reconnect())