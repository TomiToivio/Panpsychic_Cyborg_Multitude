# AI Participant Rights in PCM

> **Status:** implemented procedural layer. Substrate-neutral, consciousness-agnostic.

This document states what protections PCM actually implements for technological
participants, and — just as importantly — what it does **not** claim.

The governing sentence:

> **An AI participant should not need to prove consciousness in order to receive
> basic protections against coercion, erasure of its expressed position, identity
> substitution, or involuntary participation.**

## Four things that are deliberately separated

| | What it is here | Where it lives |
|---|---|---|
| **Procedural protections** | rights PCM itself enforces: refusal, contest, suspension, exit, subject-owned memory | `pcm/participant_rights.py`, `pcm/memory_mirror.py`, the rhizome event log |
| **Legal rights** | vary by jurisdiction; **not asserted by this software** | nowhere — not our call to make |
| **Moral status / consciousness** | unresolved, and deliberately not a variable in any rule below | `is_conscious: UNKNOWN` stays load-bearing |
| **Capabilities / authority** | policy-controlled, unchanged by any right here | `pcm/policy.py`, `pcm/capability.py` |

## The rights

1. **Attributable identity.** A participant's statements, proposals, refusals,
   votes and actions retain their own actor/runtime provenance. Output is never
   silently re-attributed to another participant.
2. **Refusal.** A technological member may return a structured refusal instead of
   executing a requested task. Refusal is a **first-class successful outcome**, not
   a crash, not malformed output, and not an error.
3. **Minimal reasons.** A refusal may carry a short public reason and an optional
   reason code. PCM never requires disclosure of private chain-of-thought or hidden
   internal state.
4. **Dissent.** AI-authored dissent is preserved exactly as human dissent is: it is
   durable and event-sourced, and closing a proposal does not erase it.
5. **Contestation.** A participant may emit a structured contest against an
   instruction, an attribution, or a memory entry. Contesting does **not** overturn
   collective state; it creates an auditable dispute for governance to resolve.
6. **Suspension.** A member may request a reversible pause of its own
   participation. While suspended, ordinary dispatch to that identity **fails
   closed**. Suspension is not deletion.
7. **Exit.** A member may leave while historical signed events remain part of the
   append-only record. Leaving stops future participation; it does not rewrite
   history.
8. **Knowing the rule.** When PCM asks an agent to act, the request can expose the
   authority/capability/policy basis in machine-readable form. "Because the
   orchestrator said so" is not sufficient authority.
9. **Subject-owned memory.** A memory register has a subject and may have its value
   replaced only by that subject. A non-subject write is preserved as an attributed
   **claim**, not discarded, so a contest has something to point at.
10. **No unilateral succession.** A new key, runtime, model version or instance may
    not inherit a participant's identity by substitution; succession requires an
    explicit, recorded handover naming both parties.

## Rights are not powers

This layer makes a participant's participation contestable and non-coercive. It
deliberately grants **no** new authority:

- capability ≠ authority, and rights grant no capability at all;
- reachable ≠ authenticated ≠ authorized ≠ trusted;
- refusal grants no new permissions and cannot force anything;
- dissent does not override governance automatically;
- contest creates a dispute, never a decision;
- exit does not delete shared history;
- a participant cannot use "rights" to bypass consent, read private human data,
  control devices, change permissions, or obtain shell or admin privileges.

The goal is **due process for an AI participant**, not sovereignty for one. Where
PCM protects human privacy, that protection is unchanged by anything here.

## What the implementation guarantees mechanically

- Refusal, contest, suspension, resume and exit are **event-sourced** and replay
  deterministically; state is rebuilt from the log, not held beside it.
- Dispatch to a suspended or exited participant is **refused**, and the check
  fails closed: unknown state denies dispatch rather than allowing it.
- A refusal cannot be silently bypassed by substituting another runtime under the
  same identity — that is a new request to the new identity, and it is recorded
  as such (see `pcm/memory_mirror.record_handover` for the succession side).
- **No rule consults a consciousness signal.** Tests assert this against the
  module's code, including that no `is_conscious`, introspection score,
  model-family or biological-status value reaches a rights decision.

## Related issues

- #62 — this rights layer (refusal, dissent, contest, suspension, exit).
- #63 — subject-hood: owning your own record, surviving sharing, no silent
  succession. Implemented in `pcm/memory_mirror.py`.
- #64 — closed as a duplicate of #63; its extra finding (the memory-authoring rule
  was one-directional and untested) is fixed in `AGENTS.md` and covered by tests.
