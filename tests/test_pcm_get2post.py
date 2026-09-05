# -*- coding: utf-8 -*-
"""Tests for the dormant GET→POST bridge (NETWORKING_STACK.md §3, §26).

Phase 0 rules under test:
- The bridge is DORMANT by default: send() raises without explicit enable.
- build_get_url() encodes destination/body/headers into the converter's
  GET query string, within the published 12 KiB limit.
- Secret-bearing headers are refused, never forwarded.
- Idempotency-Key is auto-stamped from a body fingerprint when absent.
- Destination validation: HTTPS-only, port 443, no credentials/fragments.
- send()/send_envelope() with injected fake transports deliver verbatim.

Run: python3 tests/test_pcm_get2post.py  (or via pytest)
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.pcm.envelope import Envelope, EnvelopeError
from multitude.pcm.get2post import (BridgeResult, Get2PostBridge,
                                    Get2PostConfig, content_fingerprint)
from multitude.pcm.identity import generate_identity, private_key_from_identity


def make_bridge(enabled: bool, transport=None) -> Get2PostBridge:
    cfg = Get2PostConfig(enabled=enabled)
    return Get2PostBridge(cfg, transport=transport)


def main() -> int:
    failures: list[str] = []

    # ---- 1. dormant by default ----
    bridge = make_bridge(enabled=False)
    try:
        bridge.send("https://peer.example/inbox", "{}")
        failures.append("dormant bridge allowed send() — enablement guard broken")
    except RuntimeError:
        pass
    print("[dormant] send() raises without PCM_G2P_ENABLED — OK")

    # ---- 2. URL shaping (pure) ----
    shaper = make_bridge(enabled=True)
    get_url = shaper.build_get_url(
        "https://peer.example/inbox",
        data='{"message":"hello"}',
        headers={"X-Trace": "t1"})
    parsed = urlparse(get_url)
    qs = parse_qs(parsed.query)
    if parsed.scheme != "https" or "get2post.vercel.app" not in parsed.netloc:
        failures.append(f"converter URL unexpected: {get_url[:80]}")
    if qs.get("url") != ["https://peer.example/inbox"]:
        failures.append(f"destination not encoded: {qs.get('url')}")
    if qs.get("data") != ['{"message":"hello"}']:
        failures.append(f"body not encoded: {qs.get('data')}")
    hdr = json.loads(qs["headers"][0])
    if hdr.get("X-Trace") != "t1":
        failures.append(f"headers not encoded: {hdr}")
    if "Idempotency-Key" not in hdr:
        failures.append("idempotency key not auto-stamped")
    # same body -> same key; different body -> different key
    key1 = shaper.build_get_url("https://x.example", data="a")
    key2 = shaper.build_get_url("https://x.example", data="b")
    k1 = json.loads(parse_qs(urlparse(key1).query)["headers"][0])["Idempotency-Key"]
    k2 = json.loads(parse_qs(urlparse(key2).query)["headers"][0])["Idempotency-Key"]
    if k1 == k2:
        failures.append("idempotency key ignores body content")
    print(f"[shaping] url+data+headers encoded; idem-key {k1[:8]}... stable")

    # ---- 3. 12 KiB limit enforced ----
    try:
        shaper.build_get_url("https://x.example", data="x" * (13 * 1024))
        failures.append("13 KiB payload accepted — limit missing")
    except EnvelopeError:
        pass
    print("[limit] oversized payloads rejected")

    # ---- 4. secret headers refused ----
    for secret in ({"Authorization": "Bearer x"}, {"Cookie": "a=b"},
                   {"X-API-Key": "s"}):
        try:
            shaper.build_get_url("https://x.example", data="d", headers=secret)
            failures.append(f"secret header forwarded: {list(secret)[0]}")
        except EnvelopeError:
            pass
    print("[secrets] authorization/cookie/api-key refused")

    # ---- 5. destination validation ----
    for bad in ("http://x.example", "https://user:pw@x.example",
                "https://x.example:8443", "https://x.example#frag"):
        try:
            shaper.build_get_url(bad, data="d")
            failures.append(f"bad destination accepted: {bad}")
        except EnvelopeError:
            pass
    print("[destination] non-https/credentials/port/fragment rejected")

    # ---- 6. send() through a fake transport ----
    def fake_transport(url: str) -> tuple[int | None, bytes]:
        return 200, json.dumps({
            "status": 201, "headers": {"content-type": "application/json"},
            "encoding": "utf8", "body": {"received": True}}).encode()

    live = make_bridge(enabled=True, transport=fake_transport)
    result = live.send("https://peer.example/inbox", '{"n":1}',
                       response_format="json")
    if not isinstance(result, BridgeResult) or result.upstream_status != 201:
        failures.append(f"bridge result wrong: {result}")
    if b"true" not in result.body:
        failures.append(f"upstream body lost: {result.body[:60]}")
    print("[send] upstream 201 via fake transport, body intact")

    # ---- 7. send_envelope delivers a signed envelope ----
    node_dir = Path(tempfile.mkdtemp(prefix="pcm-node-"))
    identity = generate_identity(node_dir)
    env = Envelope.create(
        "say", identity["did"], identity["did"],
        {"text": "rhizome grows", "url": "https://peer.example/inbox"})
    env.sign(private_key_from_identity(identity), identity["did"])

    calls: list[str] = []

    def capture(url: str) -> tuple[int | None, bytes]:
        calls.append(url)
        return 200, json.dumps({"status": 200, "headers": {},
                                "body": {"received": True}}).encode()

    env_bridge = make_bridge(enabled=True, transport=capture)
    env_bridge.send_envelope(env)
    if not calls:
        failures.append("send_envelope made no transport call")
    else:
        q = parse_qs(urlparse(calls[0]).query)
        body = json.loads(q["data"][0])
        if body["type"] != "say" or body["sig"] != env.sig:
            failures.append("envelope not delivered verbatim")
        if q["url"] != ["https://peer.example/inbox"]:
            failures.append(f"delivery target wrong: {q.get('url')}")
    print("[send_envelope] signed envelope delivered verbatim to inbox")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("ALL GET2POST TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# pytest wrapper (canonical suite collects this)
def test_pcm_get2post():
    assert main() == 0