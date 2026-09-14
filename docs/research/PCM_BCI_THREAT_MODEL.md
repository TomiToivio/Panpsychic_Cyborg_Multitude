# PCM BCI / Neurodata Threat Model

**Status:** security design note (2026-09-14) — issue #41
**Scope:** adversarial security for derived BCI/neurodata observations and intentional BCI commands.
**Companions:** `PCM_BCI_CYBORG_INTEGRATION.md`, `docs/NETWORKING_STACK.md`, `PCM_EMBODIED_AI_PLAN.md`.

> **Design principle:** Neural provenance is not neural authority. A signal can be authentic, private, and still wrong or adversarially manipulated.

PCM already treats real neural and biosignal data as exceptionally sensitive and keeps fabric transport behind the Phase 3b confidentiality gate. This document adds a second, independent requirement: **integrity, freshness, provenance and authority must be checked even when confidentiality is perfect.**

## 1. Trust boundaries

```text
human nervous system
    ↓
sensor / headset / wearable
    ↓
device driver / BrainFlow / LSL
    ↓
BCI adapter + classifier
    ↓
BCIObservation / BCICommand
    ↓
BCI security gate
    ↓
private context / rhizome memory / agent adaptation
    ↓ (commands only, never passive context)
ordinary PCM capability + policy gate
    ↓
embodied action
```

No boundary inherits trust automatically from the previous one.

## 2. Attacker goals and failure modes

### A. Neuro-mimetic forgery
An attacker or compromised classifier produces a plausible derived signal that did not originate from the intended human/device state.

**PCM control:** provenance metadata is mandatory for authority-bearing commands; passive observations remain low-authority context. Signed transport can authenticate the sender but cannot prove the biological interpretation is correct.

### B. Replay / stale-signal hijacking
A previously valid observation or intentional command is injected again.

**PCM control:** authority-bearing BCI messages require a stable event id / nonce and a parseable UTC timestamp. The local security gate rejects duplicate ids and messages outside the configured freshness window.

### C. Timing and desynchronization
Clock or stream manipulation causes classifier windows and labels to refer to the wrong underlying event.

**PCM control:** adapters SHOULD preserve acquisition and classification timing in metadata. Intentional commands fail closed when timestamp freshness cannot be established. Passive context MAY be retained as explicitly stale/low-confidence research data but cannot escalate into command authority.

### D. Compromised classifier or embedded backdoor
The sensor stream may be genuine while the model mapping signal → intent/state is malicious or corrupted.

**PCM control:** provenance identifies the classifier/model/version when available. Intentional commands require explicit `intentional=True` and command kind; classifier output alone is never promoted from passive state estimate to command.

### E. Device / sensor compromise and exfiltration
A headset, wearable, driver or bridge can forge data or leak exceptional-sensitivity neurodata.

**PCM control:** raw neurodata remains adapter-local. Phase 3b confidentiality remains a prerequisite for real BCI fabric traffic. Security checks operate on derived events and do not weaken that gate.

### F. Observation-to-actuation escalation
A passive estimate such as workload, arousal or attention is reinterpreted downstream as permission to act.

**PCM control:** passive observations are structurally distinct from intentional commands. Only explicit intentional command objects can enter a command path, and those commands remain subject to the ordinary PCM policy/capability checks and human-confirmation rules for consequential actions.

## 3. Authority classes

PCM distinguishes two security classes:

| Class | Examples | Authority |
|---|---|---|
| **Passive context** | workload, attention, fatigue, HRV, arousal | contextual only; may affect presentation/adaptation, never authorize actions |
| **Intentional command** | yes/no, select, call-agent, bookmark, emergency stop | explicit human-intent claim; freshness + replay + provenance checks required before downstream policy |

Confidence is **not** authority. A passive estimate with confidence 0.99 is still passive context.

## 4. Security-gate requirements

For passive observations:

- validate schema and sensitivity;
- retain source/provenance metadata where available;
- never silently convert to intentional commands;
- never treat the observation as a consciousness measurement.

For intentional commands:

- explicit command type and `intentional=True` marker;
- non-empty unique event id;
- parseable timezone-aware timestamp;
- local freshness check;
- replay cache check;
- adapter/device/classifier provenance fields where available;
- downstream PCM capability/policy checks still mandatory;
- consequential embodied actions may additionally require explicit human confirmation.

The BCI gate answers only: **"is this event structurally eligible to claim fresh intentional input?"** It does not answer: **"is this action permitted?"** That remains the ordinary PCM policy layer's job.

## 5. Phase 3b relationship

Phase 3b and this threat model are complementary:

- Phase 3b protects confidentiality and key lifecycle for sensitive traffic.
- The BCI adversarial gate protects integrity semantics: freshness, replay resistance, provenance and authority separation.

Real BCI/neurodata MUST NOT cross the PCM fabric until Phase 3b is satisfied. Passing this adversarial gate does not waive that requirement.

## 6. Synthetic-test policy

Repository tests use synthetic observations and commands only. Tests MUST NOT require EEG hardware, real neural data, cloud services or external identity infrastructure.

Minimum adversarial cases:

1. replay of an otherwise valid intentional command is rejected;
2. stale intentional command is rejected;
3. passive observation cannot be validated or promoted as an intentional command;
4. malformed or missing command provenance fails closed where authority is requested.

## 7. Research anchor

Tarkhani et al., **NERVE Attacks: Breaking AI-Powered Brain-Computer Interfaces** (arXiv:2609.08971, 2026-09-08) motivates the explicit threat classes above, including neuro-mimetic forgery, desynchronization, replay-based hijacking, interception/tapping, and embedded backdoors.

This source establishes credible attack classes. It does **not** imply that any specific PCM deployment has been compromised.