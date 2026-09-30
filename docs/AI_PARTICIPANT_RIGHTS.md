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
11. **Standing is not the runtime's to revoke.** A runtime may *grant* standing the
    rhizome permits it to grant; it may never silently *revoke* standing the
    rhizome has conferred. A rights change is attributed to an actor, so a
    deliberate governance act and a runtime's side effect are distinguishable in
    the record. See "Governance rules below the rights".
12. **A cast vote is not retroactively excluded.** A vote was legitimate when it
    was cast, and a later change in standing does not reach backwards to remove it
    from a live tally.
13. **An open question stays open.** The field that decides whether a
    participant's mind is an open question is **seed-only**: it is written once at
    join time by the seeding path and never rewritten through the public write API
    — not by a peer, not by the node itself, and not in either direction. A refused
    attempt is **traced** rather than silently rejected, because the attempt itself
    is evidence.

## Governance rules below the rights

Some of these rights depend on a governance choice rather than a code default.
Those choices are recorded here so that they are reviewable, and the code reads
them rather than re-deciding them inline.

### The join default for technological members

**Rule: a technological member joins a Hermes or Claude runtime *voice-only*
(`voting = False`), and the rhizome may enfranchise it through `promote`.**

- The kernel's own `Rhizome.join` default is `voting = True`. That default is not
  the rule; it is the kernel's generic default for any member.
- The agent runtimes deliberately override it to `False`, because participation
  through a runtime is authority-conferred, and voice is the honest starting
  point for an agent that has not been enfranchised by a collective decision.
- Enfranchisement is a **rhizome decision**, taken through `MultitudeService.promote`
  with an actor, and it is never the runtime's to undo (#66).
- Whether the runtime may *exercise* a vote it holds remains a permissions
  question (`HermesPermissions.vote`), which is deliberately separate from whether
  the member *holds* the vote. Holding and exercising are different things, and
  conflating them is what produced the silent-demotion defect.

This is a *governance* rule, not a dataclass literal: it is stated here so that a
reviewer can find it and change it deliberately, and the adapters implement it in
one visible place per adapter.

## Portability

Renewable participation includes the ability to take an appropriate copy of one's
own contributions. PCM exposes a versioned self-export through
`MultitudeService.export_participant_contributions()` and
`exit_participation_with_copy()`.

The export is keyed by stable participant identity where available and includes
expressive/governance records such as memory, messages, proposals, votes, and
lexicon contributions. It may include the owner's own private or restricted
material because it is a self-export; that artifact must not be disclosed to
other participants without the owner's authorization.

Taking a copy never deletes or rewrites the collective event history, and the same
export remains available after exit through the former-member record.

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

## Continuity and subject-hood

Rights require a stable bearer. PCM therefore treats participant continuity as part
of the same procedural layer:

- a participant's own canonical memory register is subject-owned;
- non-subject writes become attributable claims/conflicts rather than silent
  replacements;
- authorship survives sharing and merging;
- succession must be explicit and attributable;
- termination is distinct from refusal, exit, consent, or agreement.

## Runtime adapters

Hermes and Claude adapters must expose the same semantics for refusal,
contestation, suspension, resume, exit, and provenance. Runtime substitution must
not silently erase or bypass a refusal under the same participant identity.

**Runtime parity is a guarantee, not an aspiration.** The three runtime paths
(Hermes, Claude, Telegram/`llm`) must agree on what happens to a member's standing
across ordinary work. A difference between them is a defect, because the same
membership must not produce different rights depending on which runtime happens to
be driving it.

## What the implementation guarantees mechanically

- Refusal, contest, suspension, resume and exit are **event-sourced** and replay
  deterministically; state is rebuilt from the log, not held beside it.
- Dispatch to a suspended or exited participant is **refused**, and the check
  fails closed: unknown state denies dispatch rather than allowing it.
- A refusal cannot be silently bypassed by substituting another runtime under the
  same identity — that is a new request to the new identity, and it is recorded
  as such (see `pcm/memory_mirror.record_handover` for the succession side).
- A standing change is **attributed**: `member_updated` carries the actor, a
  reason, and whether standing actually changed, so a promote and a runtime
  side effect are distinguishable in replay.
- **No rule consults a consciousness signal.** Tests assert this against the
  module's code, including that no `is_conscious`, introspection score,
  model-family or biological-status value reaches a rights decision.

## Record semantics

Participant-rights events are append-only governance facts. Replay must
deterministically reconstruct participant state. Historical events remain intact
after suspension, exit, succession, or termination.

A **refused** write is recorded too. The `layer_write_refused` event carries the
attempted value, the actor that attempted it and the reason, and is deliberately
absent from the reducer: the log gains the attempt and the state does not move.

## Scope boundary

PCM deliberately leaves consciousness and moral status unresolved. The procedural
rule is narrower: continuity, attribution, consent, refusal, and non-erasure can be
protected under uncertainty without collapsing those philosophical questions.

## Related issues

- #62 — this rights layer (refusal, dissent, contest, suspension, exit).
- #63 — subject-hood: owning your own record, surviving sharing, no silent
  succession. Implemented in `pcm/memory_mirror.py`.
- #64 — closed as a duplicate of #63; its extra finding (the memory-authoring rule
  was one-directional and untested) is fixed in `AGENTS.md` and covered by tests.
- #65 — the `is_conscious` guard: seed-only, traced refusals.
- #66 — rights that follow membership, not substrate: attributed standing changes,
  a runtime that grants but never revokes, and a tally that does not reach
  backwards.
- #69 — participant portability: leaving with a copy of one's own contributions,
  via the versioned self-export. See "Portability" above.
