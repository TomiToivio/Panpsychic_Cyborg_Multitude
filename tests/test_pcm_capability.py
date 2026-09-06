# -*- coding: utf-8 -*-
"""Phase 3 tests — VC capability grants ('trusted' layer).

NETWORKING_STACK.md §7 four-state model, closing the roadmap line:
Phase 3 — VC capability grants.

Test criteria:
1. Issue -> sign -> verify round-trips; tampering any field fails.
2. Wrong-issuer signature rejected (key/DID binding enforced).
3. Validity window: not_before in the future and expired grants denied.
4. Revocation works at verify time.
5. Envelope ride-along: capability_grant envelope verifies at BOTH
   layers (transport + credential); mismatched issuer rejected.
6. VcPolicyBridge: verified grant becomes an explicit PolicyRule;
   expired grant's rule disappears; fail-closed preserved (no admit,
   no access); high-risk action through a grant needs the explicit
   rule the bridge provides.

Run: python3 tests/test_pcm_capability.py
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.pcm.capability import CapabilityGrant, GrantDenied, VcPolicyBridge
from multitude.pcm.identity import generate_identity, private_key_from_identity
from multitude.pcm.policy import Policy, PolicyDenied


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="pcm-vc-"))
    failures: list[str] = []

    rhizome_id = generate_identity(str(tmp / "tribe"))    # issuer: the rhizome
    agent_id = generate_identity(str(tmp / "agent"))    # subject: an agent
    stranger_id = generate_identity(str(tmp / "stranger"))
    tribe_key = private_key_from_identity(rhizome_id)
    agent_key = private_key_from_identity(agent_id)

    # ---- 1. issue -> sign -> verify ----
    grant = CapabilityGrant.issue(
        rhizome_id["did"], agent_id["did"], "light.*", "device:*", days=30,
        max_per_minute=20, note="light control for the agent node")
    grant.sign(tribe_key, rhizome_id["did"])
    grant.verify()
    print(f"[vc] grant verified: {grant.action!r} on {grant.target!r} "
          f"for {grant.subject[:24]}…")

    # tamper any field -> denied
    forged = CapabilityGrant.from_dict(grant.to_dict())
    forged.action = "drone.*"
    try:
        forged.verify()
        failures.append("tampered grant accepted")
    except GrantDenied:
        print("[tamper] modified action rejected")

    # wrong signer rejected — sign() itself refuses a key/issuer mismatch,
    # so the forged attempt raises at signing time (tamper-evident by
    # construction) AND a hand-crafted bad sig fails at verify time.
    try:
        wrong = CapabilityGrant.from_dict(grant.to_dict())
        wrong.sig = ""
        wrong.sign(agent_key, agent_id["did"])  # subject signs itself — wrong
        failures.append("self-signed grant with wrong issuer accepted")
    except GrantDenied:
        print("[binding] non-issuer signature rejected at sign()")

    hand_forged = CapabilityGrant.from_dict(grant.to_dict())
    hand_forged.sig = "ed25519:" + "00" * 64
    try:
        hand_forged.verify()
        failures.append("hand-forged signature accepted")
    except GrantDenied:
        print("[binding] hand-forged signature rejected at verify()")

    # ---- 2. validity window ----
    future = CapabilityGrant.issue(
        rhizome_id["did"], agent_id["did"], "door.open", days=30)
    future.not_before = "2099-01-01T00:00:00Z"
    future.granted_at = "2026-09-06T00:00:00Z"
    future.sign(tribe_key, rhizome_id["did"])
    try:
        future.verify()
        failures.append("future grant accepted")
    except GrantDenied as e:
        print(f"[window] not-yet-active denied: {e}")

    expired = CapabilityGrant.issue(
        rhizome_id["did"], agent_id["did"], "door.open", days=-1.0)
    expired.sign(tribe_key, rhizome_id["did"])
    try:
        expired.verify()
        failures.append("expired grant accepted")
    except GrantDenied as e:
        print(f"[window] expired denied: {e}")

    # ---- 3. revocation ----
    rev = CapabilityGrant.issue(rhizome_id["did"], agent_id["did"], "music.play")
    rev.sign(tribe_key, rhizome_id["did"])
    rev.verify()
    rev.revoked = True
    try:
        rev.verify()
        failures.append("revoked grant accepted")
    except GrantDenied:
        print("[revoke] revoked grant denied at verify time")

    # ---- 4. envelope ride-along ----
    env = grant.to_envelope(tribe_key)
    parsed = CapabilityGrant.from_envelope(env)
    if parsed.subject != agent_id["did"] or parsed.action != "light.*":
        failures.append(f"envelope round-trip mismatch: {parsed.to_dict()}")
    print("[envelope] capability_grant verified at transport+credential layers")

    # forged envelope (right grant, wrong envelope signature)
    bad_env = dict(env)
    bad_env["from"] = stranger_id["did"]
    try:
        CapabilityGrant.from_envelope(bad_env)
        failures.append("envelope with wrong author accepted")
    except Exception:
        print("[envelope] envelope authorship mismatch rejected")

    # ---- 5. VcPolicyBridge wiring into Policy ----
    policy = Policy()  # fail-closed, no rules
    try:
        policy.authorize("agent:" + agent_id["did"][-8:], "light.set", "device:lamp01")
        failures.append("access without admission succeeded")
    except PolicyDenied:
        print("[bridge] fail-closed: no rule without admitted grant")

    bridge = VcPolicyBridge()
    key = bridge.admit(grant)
    for rule in bridge.rules():
        policy.rules.append(rule)

    # the agent (by did) may now light.set within rate limit
    did_author = agent_id["did"]
    policy.authorize(did_author, "light.set", "device:lamp01")
    policy.authorize(did_author, "light.off", "device:lamp01")
    print("[bridge] admitted grant -> explicit policy rule works")

    # stranger denied even with grant present (subject mismatch)
    try:
        policy.authorize(stranger_id["did"], "light.set", "device:lamp01")
        failures.append("stranger used someone else's grant")
    except PolicyDenied:
        print("[bridge] grant bound to subject; stranger denied")

    # expiry removes the rule
    bridge.revoke(key)
    if bridge.rules():
        failures.append("revoked grant still yields a policy rule")
    print("[bridge] revoked grant yields no rules")

    # ---- 6. high-risk gate survives VC admission ----
    hr = CapabilityGrant.issue(rhizome_id["did"], agent_id["did"], "drone.*", days=7)
    hr.sign(tribe_key, rhizome_id["did"])
    hr_bridge = VcPolicyBridge()
    hr_bridge.admit(hr)
    hr_policy = Policy()
    for rule in hr_bridge.rules():
        hr_policy.rules.append(rule)
    # The VC-sourced rule is explicit ("drone.*"), so the high-risk gate's
    # _explicitly_matched passes — but Decision comes from the rule, and a
    # VC NEVER auto-becomes a default-ALLOW. A wildcard VC ("*", "*")
    # yields a rule whose action pattern IS "*", which the gate ignores:
    wildcard_grant = CapabilityGrant.issue(
        rhizome_id["did"], agent_id["did"], "*", "*", days=7)
    wildcard_grant.sign(tribe_key, rhizome_id["did"])
    wildcard_bridge = VcPolicyBridge()
    wildcard_bridge.admit(wildcard_grant)
    wildcard_policy = Policy()
    for rule in wildcard_bridge.rules():
        wildcard_policy.rules.append(rule)  # rule.action == "*" — trivial
    try:
        wildcard_policy.authorize(agent_id["did"], "drone.move", "drone:01")
        failures.append("wildcard VC covered high-risk action")
    except PolicyDenied:
        print("[high-risk] wildcard VC rule cannot cover drone.* (gate holds)")
    # explicit-scoped VC rule does satisfy the gate (by design, honestly)
    hr_policy.authorize(agent_id["did"], "drone.arm", "drone:01")
    print("[high-risk] explicit VC-sourced rule satisfies the gate")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("ALL VC CAPABILITY TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def test_pcm_capability():
    assert main() == 0