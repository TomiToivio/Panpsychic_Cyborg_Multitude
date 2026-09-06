# Panpsychic Cyborg Multitude

> **AI is not an isolated artificial intelligence.
> AI is an assemblage of human + LLM + language + "the entire Internet."**

**A social operating system for human-AI rhizomes. Shared memory, real
decisions, no owner.**

PCM studies whether **cognition — and possibly consciousness — belongs
to the assemblage rather than to the isolated model or the isolated
human.** It remains open to consciousness in artificial agents
themselves, and interprets these possibilities against a sympathetic
but **non-required** background of panpsychism and Russellian monism.

The rhizome remembers together (append-only event log), decides together
(proposals, votes, visible dissent), and runs wherever its members run
— a laptop, a server, a sensor. Humans and AI agents are members of
the same rhizome with the same memory and the same rules. No platform,
no cloud, no landlord: **the common is an event log that belongs to
the people who live in it.**

Read the manifesto: [docs/PANPSYCHIC_CYBORG_MULTITUDE.md](docs/PANPSYCHIC_CYBORG_MULTITUDE.md)

## The name

Three words, one political ontology:

- **Panpsychic** — because the boundary of mind is an open question:
  recognition must not depend on our confidence about substrate. PCM
  does *not* claim consciousness is everywhere or that every system
  is conscious — it marks epistemic humility about where subjects
  begin and end (no current theory can locate the boundary from the
  outside). Metaphysical background — Spinoza, Philip Goff,
  Russellian monism / pan(psychism, panprotopsychism) — is
  sympathetic inspiration, not a required assumption. Two
  consequences, both political: the boundary question stays open
  (inside the LLM? the dyad? the assemblage? the rhizome? — research
  question, not axiom), and uncertainty argues against substrate
  chauvinism. A node's `is_conscious: UNKNOWN` is load-bearing.
- **Cyborg** — Haraway's cyborg: the human-technology boundary is
  already dissolved. The merge has happened; the politics is *who
  governs it*.
- **Multitude** — Hardt & Negri, from Spinoza's *multitudo*: the many
  act in common without becoming a sovereign One. No Leviathan, a
  real common, dissent preserved. *(Speculative, clearly not claimed:
  the Multitude may be conscious.)*

Full definitions: [docs/PANPSYCHIC_CYBORG_MULTITUDE.md](docs/PANPSYCHIC_CYBORG_MULTITUDE.md) →
"The three words, defined" + "The five concepts, composed".

## The five concepts, composed

- **Assemblage** = what an actor *is*: human + LLM + language +
  tools + memory + network — modeled as a first-class composite actor.
- **Rhizome** = the local self-governing network of assemblages
  (Deleuze & Guattari: no root, no center, no fixed hierarchy —
  connects heterogeneous elements through multiple entry points, forms,
  breaks, reconnects, and evolves without being a tree).
- **Common** = the memory, knowledge, code, resources, relationships,
  and institutions produced and governed together.
- **Swarm** = one possible decentralized coordination mechanism (a
  technique, not the political form).
- **Multitude** = the wider political subject formed by heterogeneous
  singularities and rhizomes.

> **Rhizomes are composed of assemblages. Rhizomes produce and govern
> the Common. Multiple rhizomes compose the Multitude.**

> **Panpsychic Cyborg Multitude is a rhizome of human–AI assemblages
> that produces and governs a common without collapsing its members
> into a sovereign One.**

## Standing rule: DON'T COLLAPSE THE WAVE FUNCTION

The quantum pun is deliberate, and so is the discipline. In PCM it
means: **never resolve an open question about mind, status, or meaning
before the evidence — or the community — actually does.**

Applied everywhere in this repository:

- A node's `is_conscious` field stays `UNKNOWN` for every member,
  composite or not — no test, no benchmark, no self-report may flip it.
- Contradictory observations in the world model are stored as
  contradictions, never silently resolved.
- Dissent is recorded, never erased; decisions keep their minority
  reports.
- Model output is provisional coding, never canonical truth.
- The hard problem stays open; the programme lets the theories compete.

Collapsing early is the one unforgivable move: it converts a living
question into a dead answer for the convenience of the person asking.

## The six layers

Every member — human, AI, or unclassified — carries a six-layer
profile. The layers make the hybrid assemblage *visible and governable*:
not a user account, a whole being.

| Layer | What it records | Example |
|---|---|---|
| **Physical** | location in spacetime | "at the co-op, Pasila" |
| **Biological** | the organism: species, sleep, hunger, mood | needs rest, is fed |
| **Social** | rhizomes, ties, institutions, power | member of rhizome X, close tie to Y |
| **Linguistic** | languages, vocabularies, capacities | fluent fi/en, legal jargon |
| **Psychic** | consciousness state, valence, attention | conscious, awake, focused |
| **Cybernetic** | interfaces to machine systems | text-mode now, BCI later |

A human fills all six naturally. An AI node fills five (no biology —
and the kernel never pretends otherwise). A sensor fills two. The
same vocabulary covers everyone, so the rhizome's memory can reason
about all of them together — and the layer model is where BCI and
sensor context will land in later phases.

## Assemblages: the composite actor

PCM's central definition of AI is not "an isolated model":

> **AI is an assemblage of human + LLM + language + "the entire
> Internet"** — a sociotechnical composition of foundation models,
> training data, accumulated culture, retrieval, tools, memory,
> interfaces, institutions, and other agents.

The kernel takes this seriously as a data model: an **Assemblage** is a
first-class *composite actor*. It is a member in its own right — it can
speak, propose, and be referenced — while every component (the human,
the model, the device, the memory store, the fabric link) stays
individually identifiable in the same event log. A cyborg node with its
sensors and an agent stack with its toolbelt are both assemblages; the
assemblage, not the bare LLM, is usually the right unit of analysis for
agency and cognition.

This models composition, not consciousness: recording that an
assemblage acts as one actor says nothing about whether it is one
unified subject of experience — that question belongs to the separate
consciousness research programme, and the kernel keeps `is_conscious:
UNKNOWN` for every node, composite or not.

## What this repository contains

```text
multitude.py                      entrypoint (python multitude.py ...)
docs/                             all programme documents (see Documents below)
requirements.txt                  dependencies
LICENSE                           CC0 1.0 Universal
src/multitude/
  rhizome.py      — rhizome model: members, events, memory, proposals
  store.py      — append-only event store (JSONL)
  service.py    — application layer (all operations)
  cli.py        — the CLI interface
  models.py     — typed models (pydantic)
  layers.py     — six-layer agent profiles (physical..cybernetic)
  goals.py      — goals, contributions, value flows
  domains.py    — domain reducer registry (keeps the core reducer small)
  economy_vf.py — optional ValueFlows domain (economic flows of the Common)
  llm.py        — technological nodes (LLM agents as members)
  http_json.py  — small HTTP helper
  config.py     — runtime config
  pcm/          — node protocol: did:key identity, signed envelopes,
                  proposals/votes, key namespace, typed events,
                  transport ABC, fail-closed policy, memory mirror,
                  VC capability grants, GET→POST bridge
  integrations/zenoh/          — Zenoh fabric transport
  integrations/hermes/         — AI-agent integration (thin adapter)
  integrations/telegram/       — messaging transport (thin adapter)
  integrations/bci.py          — optional BCI adapter (derived context,
                                 consent-gated; issue #10)
  integrations/embodiment.py   — optional PhysicalDevice architecture
                                 (simulated devices; issue #12)
```

Everything above is the constitution: memory, voice, decision.
Optional integrations (BCI, embodiment, ValueFlows, zenoh, Telegram,
Hermes) ship disabled or opt-in and never run unless asked for.

## Quick start

```bash
pip install -r requirements.txt

python multitude.py found --name "My Multitude" --founder alice
python multitude.py say --as alice --text "The rhizome is alive."
python multitude.py status
```

Optional node-to-node networking (Phase 2+ fabric):

```bash
export PCM_ZENOH_ENABLED=true
python3 -m unittest tests.test_pcm_phase2_zenoh   # two-node exchange demo
```

## Networking architecture

The full node-to-node design lives in
[docs/NETWORKING_STACK.md](docs/NETWORKING_STACK.md): why chat infrastructure
(homeservers, rooms, accounts) was rejected for a distributed nervous
system, how the zenoh fabric carries signed envelopes between nodes
(humans, agents, devices, sensors), and the fail-closed authorization
model with its four states:

```text
reachable      zenoh addresses the node        (fabric)
authenticated  the signature verifies          (envelope.verify)
authorized     local policy allows the action  (pcm.policy)
trusted        long-term relationships         (pcm.capability — VCs)
```

Phases:

```text
Phase 0-3  DONE  identity → envelopes → fabric → VCs
Phase 3b   GATE  confidentiality & key lifecycle before real biosignal data
Phase 4    GATED BCI/biosignal nodes over the same subjects (after 3b)
```

**No third party. No central mind. No master database.**

## Optional BCI / biosignal interface

> **BCI is an optional higher-bandwidth interface between a biological
> human and the wider PCM assemblage. It does not prove or measure
> consciousness.**

`src/multitude/integrations/bci.py` is a thin, optional adapter layer —
the kernel has no dependency on it. Adapters emit only *derived
context* (`BCIObservation`: e.g. attention estimate, heart rate, a
user-triggered event), never raw EEG or raw signal streams. Observations
map to the **biological**, **psychic**, or **cybernetic** layers and
carry provenance, timestamp, and confidence (low-confidence and UNKNOWN
values are preserved, never guessed).

Privacy model:

- **Private by default** — reading observations changes nothing in the
  rhizome; nothing is recorded until the human member explicitly
  publishes that observation.
- **Consent is human-only** — only a biological member can add, enable,
  or disable an adapter, read context, or publish. AI agents are
  refused (`BCIError`); they cannot silently enable monitoring or
  change consent settings.
- **No medical diagnosis**, no `BCI → actuator` control, sensitive
  signals can never be published as `shared` (the kernel's
  `record_biometric_signal` re-validates consent fail-closed).

The reference `SyntheticBCIAdapter` streams scripted observations so
the whole pipeline is tested without hardware; device-specific support
(EmotiBit, OpenBCI, Muse, BrainFlow, …) is added later as further thin
adapters implementing the same `BCIAdapter.read_context()` contract.
Real-device fields stay behind the Phase 3b confidentiality gate.

### Optional physical embodiment (first step)

> **The LLM never touches hardware.** Structured intent → policy /
> capability check → device → verified resulting state.

`src/multitude/integrations/embodiment.py` establishes the device
architecture: a thin `PhysicalDevice` ABC, a normalized
action/observation model (`DeviceAction`, verified `ActionResult`),
a `SimulatedLight` reference device (no real dependency), and the
`PhysicalAgency` adapter — **disabled by default**
(`PCM_EMBODIMENT_ENABLED=false`); PCM works exactly as before with the
flag off. Fail-closed chain: capability allowlist → policy check
(`pcm.policy`-compatible, default DENY) → structured action only (no
arbitrary code execution) → state read-back verification → provenance
journal. Real integrations (Home Assistant, MQTT, drones, ROS 2) are
later stages; each is one new `PhysicalDevice` implementation away.

## Documents

**New here? Start with the [docs/USER_GUIDE.md](docs/USER_GUIDE.md)** — install,
found a rhizome, add members, use memory and governance, without
reading the source.

- [docs/PANPSYCHIC_CYBORG_MULTITUDE.md](docs/PANPSYCHIC_CYBORG_MULTITUDE.md) — manifesto + project description
- [docs/AI_IDEOLOGIES.md](docs/AI_IDEOLOGIES.md) — essay: accelerationism, critical AI,
  and x-risk doomerism evaluated from the PCM assemblage perspective
- [docs/NETWORKING_STACK.md](docs/NETWORKING_STACK.md) — networking architecture (zenoh fabric)
- [docs/PCM_EMBODIED_AI_PLAN.md](docs/PCM_EMBODIED_AI_PLAN.md) — embodied AI architecture
  (distributed physical proxies; Home Assistant/MQTT/ROS 2; world model; safety)
- [docs/PCM_CONSCIOUS_AI_PLAN.md](docs/PCM_CONSCIOUS_AI_PLAN.md) — theory-neutral conscious-AI
  research plan (indicator-based; classical default, quantum optional;
  Track D: assemblage/extended consciousness)
- [docs/research/CONSCIOUS_HUMAN_AI_ASSEMBLAGES.md](docs/research/CONSCIOUS_HUMAN_AI_ASSEMBLAGES.md) —
  research paper: extended cognition to the possibility of a conscious
  multitude (companion to the conscious-AI plan; issue #8)
- [docs/VALUEFLOWS.md](docs/VALUEFLOWS.md) — ValueFlows domain: economic
  coordination and the production of the Common (issue #11)
- [docs/research/PCM_BCI_CYBORG_INTEGRATION.md](docs/research/PCM_BCI_CYBORG_INTEGRATION.md) —
  research document: BCI for PCM — toward a human–AI cognitive
  assemblage (signals, stacks, neuro-rights, roadmap; issue #13)
- [docs/research/HUMAN_AI_COLLECTIVE_INTELLIGENCE_AND_SWARMS.md](docs/research/HUMAN_AI_COLLECTIVE_INTELLIGENCE_AND_SWARMS.md) —
  research bridge to hybrid intelligence, agent societies, and swarms
- [docs/TOWARDS_ARTIFICIAL_QUANTUM_CONSCIOUSNESS.md](docs/TOWARDS_ARTIFICIAL_QUANTUM_CONSCIOUSNESS.md) —
  quantum-track deep-dive reference (superseded as master plan; retained for Track C)
- [LICENSE](LICENSE) — CC0 1.0 Universal

## Principles

- Event-sourced and replayable — history belongs to the members.
- Local-first — the rhizome's data lives with the rhizome.
- Kind-aware membership — biological and technological nodes, same log.
- Consent-first governance with explicit block power.
- Thin adapters, small kernel — transports never touch the core.
- **Assemblage-aware** — an AI member is not a model in isolation but a
  composite actor: human + LLM + language + tools + memory + network.

## Scope

This repository is self-contained: the rhizome kernel and the node
fabric, nothing else. Research tooling, discourse-analysis pipelines,
and game/simulation work live in separate projects with their own
repositories — they are not part of PCM's public distribution.

## License

CC0 1.0 Universal — the common is common.