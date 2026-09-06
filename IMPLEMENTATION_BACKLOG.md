# PCM Implementation Backlog

This backlog converts the external project inspirations into concrete, prioritized work in the repository. Each item is mapped to the exact code and architecture files where it should live and includes the relevant project inspiration behind it.

The ordering keeps the current merged kernel stable while expanding it in the directions best fit for PCM:

- local-first, append-only memory
- worker-co-op and commons governance
- explicit dissent and provenance
- human + AI parity in agent structure
- text-first interfaces before larger embodiment systems

---

## Priority 0 — Preserve and harden the merged kernel

### 0.1 Final merge and regression safety

Project inspirations:
- Sensorica / True Commons / DisCO / commons governance patterns
- repo merge-safety guidance from concurrent agent work

Target files:
- [src/multitude/tribe.py](src/multitude/tribe.py)
- [src/multitude/service.py](src/multitude/service.py)
- [src/multitude/store.py](src/multitude/store.py)
- [tests/test_tribe.py](tests/test_tribe.py)
- [ARCHITECTURE.md](ARCHITECTURE.md)

Scope:
- keep the library-level event-sourced root stable
- protect against replay bugs, double-apply issues, and schema drift
- verify the project still passes the current kernel test suite

Acceptance criteria:
- all existing kernel tests still pass
- no silent overwrite of member, proposal, or goal history
- architecture and implementation remain aligned

---

## Priority 1 — Governance and commons work model

### 1.1 Add a resource + work ontology to the domain model

Project inspirations:
- hREA
- Sensorica
- True Commons

Target files:
- [src/multitude/models.py](src/multitude/models.py)
- [src/multitude/goals.py](src/multitude/goals.py)
- [src/multitude/tribe.py](src/multitude/tribe.py)
- [src/multitude/service.py](src/multitude/service.py)

Scope:
- formally model work resources, obligations, and value flows
- separate task ownership from goal ownership
- represent co-op planning and member labor in a durable, queryable way

Planned additions:
- resource types and resource state
- event flows for task/work commitments
- member-to-task/goal attribution with provenance
- ledger-friendly accounting of costs and revenue

Acceptance criteria:
- real tasks and contribution data can be tracked without hidden mutable state
- work tracking is serialized through the same event log pattern as proposals and goals

### 1.2 Add explicit commons governance hooks

Project inspirations:
- DisCO
- True Commons
- Nondominium

Target files:
- [PLAN.md](PLAN.md)
- [src/multitude/goals.py](src/multitude/goals.py)
- [src/multitude/tribe.py](src/multitude/tribe.py)
- [src/multitude/service.py](src/multitude/service.py)

Scope:
- clarify tribe governance beyond a generic “vote and win” model
- add explicit co-op operation categories: labor, value, care, and maintenance
- capture governance decisions in terms of shared work and responsibility, not just simple ballots

Acceptance criteria:
- governance can represent more than majority voting
- worker co-op obligations and shared labor are recorded in the same durable system

---

## Priority 2 — Local-first memory and selective sharing

### 2.1 Expand memory boundaries and provenance

Project inspirations:
- Noosphere
- local-first memory systems
- shared social memory patterns in AGENTS.md and ARCHITECTURE.md

Target files:
- [src/multitude/store.py](src/multitude/store.py)
- [src/multitude/tribe.py](src/multitude/tribe.py)
- [src/multitude/service.py](src/multitude/service.py)
- [AGENTS.md](AGENTS.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)

Scope:
- distinguish tribe memory from personal agent memory
- strengthen provenance tags for human versus AI-authored entries
- add selective-sharing metadata rather than implicit global access

Planned additions:
- memory visibility levels
- author provenance and source attribution
- memory replay filters by scope or audience

Acceptance criteria:
- the memory model states exactly what is shared, what is personal, and what is imported
- no memory item silently loses provenance or authorship

### 2.2 Add durable search and recall by topic, actor, and source

Project inspirations:
- noosphere-like memory graphs
- memory-first social systems

Target files:
- [src/multitude/tribe.py](src/multitude/tribe.py)
- [src/multitude/service.py](src/multitude/service.py)
- [src/multitude/models.py](src/multitude/models.py)

Scope:
- support contextual retrieval across memory, proposals, decisions, and notes
- produce search outputs that preserve scope and provenance

Acceptance criteria:
- memory search can answer “what did the tribe decide about X?” or “which agent said Y?” without rewriting history

---

## Priority 3 — Deliberation and disagreement mapping

### 3.1 Upgrade proposal presentation to plural deliberation, not only binary voting

Project inspirations:
- Pol.is
- Plurality
- disagreement mapping

Target files:
- [src/multitude/tribe.py](src/multitude/tribe.py)
- [src/multitude/service.py](src/multitude/service.py)
- [src/multitude/llm.py](src/multitude/llm.py)
- [src/multitude/models.py](src/multitude/models.py)

Scope:
- preserve dissent as a first-class signal
- surface vote reasons and block positions in proposal views
- show “cluster” or “theme” summaries without flattening disagreement

Planned additions:
- proposal rationales aggregation
- dissent summary by member or theme
- supporting context extraction from prior memory or task notes

Acceptance criteria:
- proposal outputs show not only counts, but the reasoned disagreement that shaped the outcome

### 3.2 Add AI counsel and synthesis as a deliberative layer, not sovereign ruler

Project inspirations:
- Plurality
- Pol.is
- AI-as-sensemaking rather than AI-as-authority

Target files:
- [src/multitude/llm.py](src/multitude/llm.py)
- [src/multitude/service.py](src/multitude/service.py)
- [src/multitude/tribe.py](src/multitude/tribe.py)

Scope:
- keep LLM-generated counsel clearly labeled as counsel
- add context-to-counsel prompts grounded in shared memory and proposals
- do not treat AI output as the final decision source

Acceptance criteria:
- AI suggestions remain distinct from human consent, voting, and objecting
- the system makes the distinction explicit in display and records

---

## Priority 4 — Research import and social data capture

### 4.1 Finish the normalized scraper and 4CAT-compatible import/export pipeline

Project inspirations:
- Zeeschuimer patterns
- old TikTok scraper patterns
- 4CAT import/export compatibility

Target files:
- [src/multitude/scraping](src/multitude/scraping)
- [src/multitude/store.py](src/multitude/store.py)
- [data](data)
- [ARCHITECTURE.md](ARCHITECTURE.md)

Scope:
- normalize social capture into durable records with provenance
- export to SQLite and CSV while keeping raw collections
- provide 4CAT-like import adaptation with explicit metadata

Acceptance criteria:
- scraped data lands in a structured local store rather than ad hoc dumps
- import adapters can map 4CAT-like records into the repo’s event/log model without contaminating shared tribe memory

### 4.2 Separate captured research from canonical tribe memory

Project inspirations:
- social-data capture and research workflows
- local-first memory boundaries

Target files:
- [src/multitude/store.py](src/multitude/store.py)
- [src/multitude/service.py](src/multitude/service.py)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [data](data)

Scope:
- stop treating research ingestion as if it were shared tribal memory by default
- require explicit import or event conversion to move capture data into the tribe layer

Acceptance criteria:
- research scraping and archive ingestion remain clearly separated from governance and member memory

---

## Priority 5 — Biological, device, and sensing layer

### 5.1 Add a clean sensing pipeline for physical and biological inputs

Project inspirations:
- Michael Levin / TAME
- sensor and device telemetry patterns
- BCI / wearable / environment work

Target files:
- [src/multitude/layers.py](src/multitude/layers.py)
- [src/multitude/models.py](src/multitude/models.py)
- [OPENBCI_PLAN.md](OPENBCI_PLAN.md)
- [LAYERS_PLAN.md](LAYERS_PLAN.md)
- [src/multitude/tribe.py](src/multitude/tribe.py)

Scope:
- extend the six-layer model to represent device and biosignal inputs without collapsing them into direct governance actions
- keep biological and cybernetic factors separate but linkable

Acceptance criteria:
- device and sensor events can be recorded with provenance and opt-in semantics
- biological and physical signals do not override consensus or shared-memory boundaries

### 5.2 Formalize a consent-first data model for health and awareness signals

Project inspirations:
- shared-memory + consent-first governance
- privacy-conscious local-first coordination

Target files:
- [src/multitude/models.py](src/multitude/models.py)
- [src/multitude/layers.py](src/multitude/layers.py)
- [src/multitude/tribe.py](src/multitude/tribe.py)
- [SPEC.md](SPEC.md)

Scope:
- add explicit opt-in and scope markers for sensitive signals
- separate readable health metadata from decisive governance data

Acceptance criteria:
- health or neuro-sensitive records cannot be silently treated as shared tribal memory

---

## Priority 6 — Future research and speculative exploration

### 6.1 Keep broader grand-system ideas in research mode

Project inspirations:
- Global Brain / Principia Cybernetica
- Levin / multi-scale agency
- A(I)nimism / Institute of the Cosmos
- other speculative network or consciousness frameworks

Target files:
- [README.md](README.md)
- [PHILOSOPHY.md](PHILOSOPHY.md)
- [whitepaper.md](whitepaper.md)
- [manifesto.md](manifesto.md)
- [PLAN.md](PLAN.md)

Scope:
- keep these as conceptual and philosophical context
- do not let them drive production features without a file-level operational mapping

Acceptance criteria:
- speculative ideas remain explicitly documented as future framing, not implementation requirements

---

## Priority 7 — Dependency policy: agent frameworks

### 7.1 LangGraph and LlamaIndex are NOT dependencies — decision record (2026-09-06)

Project inspirations:
- maintainer question: "Pitäisikö meidän käyttää LangGraph tai LlamaIndex?"
- PCM integration map: prefer raw primitives over orchestration platforms

Decision: **neither.** Rationale (so nobody has to re-derive it):

**LangGraph — rejected: it solves a problem PCM does not have.**
1. Orchestration already exists. The Transport ABC + zenoh fabric +
   capability grants + fail-closed Policy (`pcm/policy.py`) already
   route agent traffic. LangGraph's core is a state machine steering
   agent flow — adding it would create a **second authority**, which
   violates the architecture's one-rule-per-layer design.
2. Graph-as-code freezes a dynamic network. PCM agents discover each
   other via fabric liveliness + capability grants, not a static graph
   defined in code. A LangGraph graph is an org chart; the PCM fabric
   is a city.
3. It is an orchestration platform — the exact category the roadmap
   lists as rejected (platform-owned choke points do not compose into
   a multitude).

**LlamaIndex — rejected for the kernel, allowed in analysis projects:**
1. It is a data-ingestion/RAG framework. PCM memory is events.jsonl —
   append-only, provenance-first. Vector-store abstraction would make
   memory *non-truthful*: similarity search is not provenance-bound
   (it cannot answer "who asserted this, when").
2. Acceptable *outside* the kernel where provenance rules differ
   (e.g. document search in the discourse-analysis sister work) — a
   separate project's tool, never a kernel dependency.

**The test (apply before accepting ANY framework dependency):**

> If a library proposes that it *is* the architecture, it does not
> belong in PCM. If it offers isolated primitives, it does.

Examples of primitives that pass: pydantic, cryptography,
eclipse-zenoh. Examples that fail: LangGraph, LlamaIndex (kernel),
AutoGen, CrewAI — anything whose selling point is "we are the
orchestration layer".

**Interop stays wire-level, not code-level:** when PCM must talk to
foreign agents (MCP / A2A / whatever survives the protocol war), those
are thin adapters over the Transport ABC — the same pattern as the
Hermes and Telegram integrations. Never an embedded framework.

Target files:
- [requirements.txt](requirements.txt) — stays minimal; no framework entries
- [src/multitude/pcm/transport.py](src/multitude/pcm/transport.py) — the only
  place an interop adapter may appear
- [NETWORKING_STACK.md](NETWORKING_STACK.md) §"Explicitly NOT adopted" —
  add orchestration platforms alongside Matrix/Holochain/IPFS

Acceptance criteria:
- requirements.txt contains no agent-framework dependency
- any PR adding one must reopen this decision, not silently override it

---

## phased execution roadmap

### Phase 1: stabilize and align
- finalize merge safety in [src/multitude/tribe.py](src/multitude/tribe.py)
- lock down shared memory provenance in [src/multitude/store.py](src/multitude/store.py)
- validate against [tests/test_tribe.py](tests/test_tribe.py)

### Phase 2: governance and work
- add common resource/event work model in [src/multitude/models.py](src/multitude/models.py)
- expand co-op goals and labor tracking in [src/multitude/goals.py](src/multitude/goals.py)
- align with [PLAN.md](PLAN.md)

### Phase 3: deliberation and sensemaking
- extend proposal and dissent output in [src/multitude/service.py](src/multitude/service.py)
- keep AI counsel distinct in [src/multitude/llm.py](src/multitude/llm.py)

### Phase 4: instruments and context streams
- integrate biological and device layers via [src/multitude/layers.py](src/multitude/layers.py)
- coordinate with [OPENBCI_PLAN.md](OPENBCI_PLAN.md) and [LAYERS_PLAN.md](LAYERS_PLAN.md)

### Phase 5: research and ecosystem integration
- keep social capture + imports modular and compartmentalized in [src/multitude/scraping](src/multitude/scraping)
- keep theory work in the conceptual docs without leaking into the kernel

---

## Recommended order of implementation

1. [src/multitude/store.py](src/multitude/store.py)
2. [src/multitude/tribe.py](src/multitude/tribe.py)
3. [src/multitude/models.py](src/multitude/models.py)
4. [src/multitude/goals.py](src/multitude/goals.py)
5. [src/multitude/service.py](src/multitude/service.py)
6. [src/multitude/llm.py](src/multitude/llm.py)
7. [src/multitude/layers.py](src/multitude/layers.py)
8. [src/multitude/scraping](src/multitude/scraping)
9. [OPENBCI_PLAN.md](OPENBCI_PLAN.md)
10. conceptual docs: [PLAN.md](PLAN.md), [README.md](README.md), [PHILOSOPHY.md](PHILOSOPHY.md)

This order preserves the current architecture while making the best use of the external project influences already identified in the PCM integration map.
