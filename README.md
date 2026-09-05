# Panpsychic Cyborg Multitude

**A social operating system for human-AI tribes. Shared memory, real
decisions, no owner.**

The tribe remembers together (append-only event log), decides together
(proposals, votes, visible dissent), and runs wherever its members run
— a laptop, a server, a sensor. Humans and AI agents are members of
the same tribe with the same memory and the same rules. No platform,
no cloud, no landlord: **the common is an event log that belongs to
the people who live in it.**

Read the manifesto: [PANPSYCHIC_CYBORG_MULTITUDE.md](PANPSYCHIC_CYBORG_MULTITUDE.md)

## The name

Three words, one political ontology:

- **Panpsychic** — consciousness is fundamental (Spinoza, Philip
  Goff); recognition must not depend on substrate. An AI node's
  `is_conscious: UNKNOWN` is load-bearing: recognition precedes proof.
- **Cyborg** — Haraway's cyborg: the human-technology boundary is
  already dissolved. The merge has happened; the politics is *who
  governs it*.
- **Multitude** — Hardt & Negri, from Spinoza's *multitudo*: the many
  act in common without becoming a sovereign One. No Leviathan, a
  real common, dissent preserved.

Full definitions: [PANPSYCHIC_CYBORG_MULTITUDE.md](PANPSYCHIC_CYBORG_MULTITUDE.md) →
"The three words, defined".

## The six layers

Every member — human, AI, or unclassified — carries a six-layer
profile. The layers make the hybrid assemblage *visible and governable*:
not a user account, a whole being.

| Layer | What it records | Example |
|---|---|---|
| **Physical** | location in spacetime | "at the co-op, Pasila" |
| **Biological** | the organism: species, sleep, hunger, mood | needs rest, is fed |
| **Social** | tribes, ties, institutions, power | member of tribe X, close tie to Y |
| **Linguistic** | languages, vocabularies, capacities | fluent fi/en, legal jargon |
| **Psychic** | consciousness state, valence, attention | conscious, awake, focused |
| **Cybernetic** | interfaces to machine systems | text-mode now, BCI later |

A human fills all six naturally. An AI node fills five (no biology —
and the kernel never pretends otherwise). A sensor fills two. The
same vocabulary covers everyone, so the tribe's memory can reason
about all of them together — and the layer model is where BCI and
sensor context will land in later phases.

## What this repository contains

```
multitude.py                      entrypoint (python multitude.py ...)
PANPSYCHIC_CYBORG_MULTITUDE.md    manifesto + project description
NETWORKING_STACK.md               node-to-node networking architecture
                                  (zenoh fabric, namespace, events, policy)
requirements.txt                  dependencies
LICENSE                           CC0 1.0 Universal
src/multitude/
  tribe.py      — tribe model: members, events, memory, proposals
  store.py      — append-only event store (JSONL)
  service.py    — application layer (all operations)
  cli.py        — the CLI interface
  models.py     — typed models (pydantic)
  layers.py     — six-layer agent profiles (physical..cybernetic)
  goals.py      — goals, contributions, value flows
  llm.py        — technological nodes (LLM agents as members)
  http_json.py  — small HTTP helper
  config.py     — runtime config
  pcm/          — node protocol: did:key identity, signed envelopes,
                  proposals/votes, memory mirror, VC capability grants,
                  key namespace, typed events, transport ABC,
                  fail-closed policy
  integrations/zenoh/          — Zenoh fabric transport (Phase 2)
  integrations/hermes/         — AI-agent integration (thin adapter)
  integrations/telegram/       — messaging transport (thin adapter)
```

No simulation. No scrapers. No experimental sensors. Just the
constitution: memory, voice, decision.

## Quick start

```bash
pip install -r requirements.txt

python multitude.py found --name "My Multitude" --founder alice
python multitude.py say --as alice --text "The tribe is alive."
python multitude.py status
```

Optional node-to-node networking (Phase 2+ fabric):

```bash
export PCM_ZENOH_ENABLED=true
python3 -m unittest tests.test_pcm_phase2_zenoh   # two-node exchange demo
```

## Networking architecture

The full node-to-node design lives in
[NETWORKING_STACK.md](NETWORKING_STACK.md): why chat infrastructure
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
Phase 4    NEXT  BCI/biosignal nodes over the same subjects
```

**No third party. No central mind. No master database.**

## Documents

- [PANPSYCHIC_CYBORG_MULTITUDE.md](PANPSYCHIC_CYBORG_MULTITUDE.md) — manifesto + project description
- [NETWORKING_STACK.md](NETWORKING_STACK.md) — networking architecture (zenoh fabric)
- [LICENSE](LICENSE) — CC0 1.0 Universal

## Scope

This repository is self-contained: the tribe kernel and the node
fabric, nothing else. Research tooling, discourse-analysis pipelines,
and game/simulation work live in separate projects with their own
repositories — they are not part of PCM's public distribution.
