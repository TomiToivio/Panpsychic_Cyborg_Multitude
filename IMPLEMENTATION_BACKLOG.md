# PCM Implementation Backlog

> **Source-of-truth rule:** when this backlog conflicts with current code or canonical documentation, the current repository wins. In particular, use `README.md`, `docs/USER_GUIDE.md`, `docs/NETWORKING_STACK.md`, `docs/PCM_CONSCIOUS_AI_PLAN.md`, and the code under `src/multitude/` as authoritative. This file is only a prioritized TODO index.

This backlog is intentionally narrow. It contains only work that is still relevant to the current **Rhizome** architecture.

## Current architecture already implemented

The following are **not backlog items** anymore:

- event-sourced Rhizome kernel in `src/multitude/rhizome.py` + `src/multitude/store.py`;
- six-layer member profiles in `src/multitude/layers.py`;
- canonical service layer in `src/multitude/service.py`;
- ValueFlows/Common economic domain in `src/multitude/economy_vf.py` and `docs/VALUEFLOWS.md`;
- consent-first BCI adapter in `src/multitude/integrations/bci.py` and `docs/research/PCM_BCI_CYBORG_INTEGRATION.md`;
- embodied-device architecture in `src/multitude/integrations/embodiment.py` and `docs/PCM_EMBODIED_AI_PLAN.md`;
- did:key identity, signed envelopes, namespaces, transport, policy and capability grants under `src/multitude/pcm/`;
- Zenoh fabric integration under `src/multitude/integrations/zenoh/`;
- Hermes and Claude Code as thin technological-member adapters under `src/multitude/integrations/hermes/` and `src/multitude/integrations/claude/`;
- agent self-knowledge/introspection experiments under `src/multitude/integrations/introspection/`;
- IIT and Active-Inference toy experiments under `experiments/`;
- theory-neutral consciousness research docs under `docs/research/`.

Legacy names such as `tribe` may still appear in serialized fields, compatibility APIs or historical prose. New implementation work should use **Rhizome** terminology unless compatibility requires otherwise.

---

## Priority 0 — Kernel reliability and provenance

### 0.1 Keep replay and schema evolution boring

Current files:

- `src/multitude/rhizome.py`
- `src/multitude/store.py`
- `src/multitude/service.py`
- `src/multitude/models.py`
- `tests/`

Work:

- protect replay against double-apply and schema drift;
- keep event provenance explicit;
- add migrations only when needed and keep old event logs readable;
- keep mutating behavior behind the canonical service/policy paths.

Acceptance:

- append-only history is never silently rewritten;
- replay remains deterministic;
- new state can be reconstructed from persisted events.

---

## Priority 1 — Selective sharing and memory boundaries

### 1.1 Make shared vs private vs agent-scoped memory more explicit

Current files:

- `src/multitude/rhizome.py`
- `src/multitude/store.py`
- `src/multitude/service.py`
- `src/multitude/models.py`
- `AGENTS.md`

Work:

- strengthen visibility/audience metadata where the current model is too coarse;
- preserve human-, agent-, imported- and system-derived provenance;
- keep personal/runtime-local caches distinct from shared Rhizome memory;
- make search respect visibility and provenance.

Acceptance:

- no memory item silently loses authorship or scope;
- agent-local state is not mistaken for collective memory;
- search results can explain who asserted what and when.

### 1.2 Improve durable recall across memory, proposals and decisions

Work:

- contextual retrieval by topic, actor, source and decision;
- return source event IDs/provenance with search results;
- preserve dissent and superseded positions rather than flattening history.

---

## Priority 2 — Deliberation and disagreement mapping

Current files:

- `src/multitude/rhizome.py`
- `src/multitude/service.py`
- `src/multitude/models.py`
- `src/multitude/llm.py`

Work:

- make proposal views expose reasons, dissent and blocking rationales clearly;
- support plural summaries/clusters without turning them into a single synthetic consensus;
- keep AI counsel/proposals separate from accepted collective decisions.

Acceptance:

- an AI suggestion is visibly a proposal/observation, not the Multitude's position;
- minority reasoning remains inspectable after a decision.

---

## Priority 3 — Commons / cooperative institutional layer

ValueFlows primitives already exist. Remaining work should focus on **institutional use**, not rebuilding the ontology.

Current files:

- `src/multitude/economy_vf.py`
- `src/multitude/goals.py`
- `src/multitude/service.py`
- `docs/VALUEFLOWS.md`

Work:

- connect goals/work/contributions to cooperative planning where useful;
- model care, maintenance, financing and common infrastructure explicitly when real use cases require them;
- keep accounting/provenance event-sourced.

Acceptance:

- work and resource coordination can be inspected without hidden mutable state;
- economic coordination does not become a centralized authority layer.

---

## Priority 4 — Distributed fabric hardening

Canonical reference: `docs/NETWORKING_STACK.md`.

Current files:

- `src/multitude/pcm/`
- `src/multitude/integrations/zenoh/`

Work:

- continue confidentiality/key-lifecycle work before sensitive biosignal traffic;
- test multi-node failure, reconnect, replay and adversarial cases;
- preserve `reachable != authenticated != authorized != trusted`;
- keep routers/transports as infrastructure, never authority.

Acceptance:

- fail closed under missing/invalid identity or capability grants;
- no transport can bypass PCM policy;
- sensitive data does not ride the fabric before its privacy gate is satisfied.

---

## Priority 5 — Human/AI/device boundary experiments

Current files:

- `src/multitude/integrations/bci.py`
- `src/multitude/integrations/embodiment.py`
- `src/multitude/integrations/introspection/`
- `experiments/active_inference/`
- `experiments/iit/`
- `docs/research/`

Work:

- keep adding **small, explicit experiments** that separate agency, self-model, causal organization, relation and phenomenology;
- prefer synthetic/mock devices and tiny causal systems first;
- preserve raw neural/device data locally and publish derived context only when consent allows;
- continue self-knowledge calibration without treating introspection as consciousness evidence.

Acceptance:

- every experiment states what it measures and what it does **not** establish;
- no biosignal, introspection metric or theory proxy becomes an authorization signal.

---

## Priority 6 — Machine-consciousness comparative research

Canonical files:

- `docs/PCM_CONSCIOUS_AI_PLAN.md`
- `docs/research/MACHINE_CONSCIOUSNESS_THEORY_MAP.md`
- `data/theory/machine_consciousness_indicators.yaml`
- `docs/IIT_AND_PYPHI.md`
- `docs/research/ACTIVE_INFERENCE_AND_PCM.md`
- `docs/PANCYBERPSYCHISM.md`
- `docs/research/AIDIFICATION_AND_RELATIONAL_SELFHOOD.md`
- `docs/research/CONSCIOUS_HUMAN_AI_ASSEMBLAGES.md`

Work:

- maintain theory-specific indicators and falsifiers;
- distinguish behavioral, functional, causal, relational and substrate evidence;
- track current-AI vs future-architecture claims separately;
- keep panpsychism/Russellian monism as ontology/background, not an engineering shortcut;
- never turn indicator counts into a synthetic consciousness percentage.

---

## Priority 7 — Agent runtimes remain adapters

Canonical files:

- `AGENTS.md`
- `HERMES.md`
- `CLAUDE.md`
- `src/multitude/integrations/hermes/`
- `src/multitude/integrations/claude/`
- `src/multitude/pcm/transport.py`

Decision remains:

> If a library proposes that it **is** the architecture, it does not belong in the PCM kernel. If it offers isolated primitives that preserve PCM's authority boundaries, it may.

Therefore:

- no LangGraph, AutoGen, CrewAI or similar orchestration layer in the kernel;
- no LlamaIndex as canonical memory architecture;
- foreign agent protocols belong behind thin adapters/wire boundaries;
- Hermes, Claude and future runtimes share PCM identity, permissions, memory and transport semantics.

---

## Explicitly out of scope: scraping / social-data collection

PCM **does not contain or plan a scraper subsystem**. Do not reintroduce `src/multitude/scraping` or a social-media collection CLI here.

Collection and computational discourse-analysis work belongs in dedicated research projects such as LaclauGPT/AI26, 4CAT/Zeeschuimer-based workflows, or other external data pipelines. PCM may consume explicitly imported research artifacts through a future narrow adapter, but captured social data is not Rhizome memory by default.

---

## Recommended implementation order

1. replay/provenance hardening;
2. selective memory boundaries and provenance-aware search;
3. richer deliberation/dissent views;
4. distributed confidentiality and adversarial fabric tests;
5. cooperative institutional use of existing ValueFlows primitives;
6. bounded BCI/embodiment/introspection experiments;
7. theory-map maintenance and research comparisons.

Keep the kernel small. Keep experiments optional. Keep authority explicit.
