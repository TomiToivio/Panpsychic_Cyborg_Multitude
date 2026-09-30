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
