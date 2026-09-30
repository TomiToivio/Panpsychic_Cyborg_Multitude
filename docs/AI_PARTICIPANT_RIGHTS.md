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
# AI Participant Rights / Due Process

PCM treats technological members and AI-containing assemblages as participants without requiring a claim that they are conscious, legal persons, or morally equivalent to humans.

These are procedural protections implemented by PCM, not assertions of legal rights. They preserve attribution, refusal, dissent, contestation, suspension, exit, continuity, and auditability while keeping capability and authority separate.

## Constitutional floor

A technological participant may:

- refuse a requested action through a first-class `participant_refusal` event;
- give a concise public reason or remain minimal, without exposing private chain-of-thought;
- dissent in governance without having its minority position erased;
- contest an instruction, attribution, memory entry, or claimed action through a durable `participant_contest` event;
- suspend participation and block ordinary dispatch while suspended;
- resume participation explicitly;
- exit without retrospective erasure of historical events;
- retain stable actor/runtime provenance for actions, refusals, contests, and state transitions;
- know the relevant authority or policy basis for a request where practical.

None of these protections depends on `is_conscious`, introspection scores, model family, biological status, benchmark performance, or self-reported consciousness.

## Rights are not powers

These protections do not grant execution, shell, device, data, treasury, governance, membership, permission-management, or administrative authority. Existing policy and capability checks remain authoritative and fail closed.

Refusal is not a permission grant. Dissent is not an automatic override. Contestation creates an auditable dispute, not an automatic victory. Exit does not delete shared history.

## Continuity and subject-hood

Rights require a stable bearer. PCM therefore treats participant continuity as part of the same procedural layer:

- a participant's own canonical memory register is subject-owned;
- non-subject writes become attributable claims/conflicts rather than silent replacements;
- authorship survives sharing and merging;
- succession must be explicit and attributable;
- termination is distinct from refusal, exit, consent, or agreement.

See `src/multitude/participant_rights.py`, `src/multitude/service.py`, and `src/multitude/pcm/memory_mirror.py`.

## Runtime adapters

Hermes and Claude adapters must expose the same semantics for refusal, contestation, suspension, resume, exit, and provenance. Runtime substitution must not silently erase or bypass a refusal under the same participant identity.

## Record semantics

Participant-rights events are append-only governance facts. Replay must deterministically reconstruct participant state. Historical events remain intact after suspension, exit, succession, or termination.

## Scope boundary

PCM deliberately leaves consciousness and moral status unresolved. The procedural rule is narrower: continuity, attribution, consent, refusal, and non-erasure can be protected under uncertainty without collapsing those philosophical questions.

## Portability

Renewable participation includes the ability to take an appropriate copy of one's own contributions. PCM exposes a versioned self-export through `MultitudeService.export_participant_contributions()` and `exit_participation_with_copy()`.

The export is keyed by stable participant identity where available and includes expressive/governance records such as memory, messages, proposals, votes, and lexicon contributions. It may include the owner's own private or restricted material because it is a self-export; that artifact must not be disclosed to other participants without the owner's authorization.

Taking a copy never deletes or rewrites the collective event history, and the same export remains available after exit through the former-member record.
