# Panpsychic Cyborg Multitude — minimal public distribution

**PCM is a social operating system for human-AI tribes: shared memory,
deliberation, decisions, and member layers — event-sourced, local-first,
CC0.**

Read the manifesto: [PANPSYCHIC_CYBORG_MULTITUDE.md](PANPSYCHIC_CYBORG_MULTITUDE.md)
— the philosophy and the project description in one document.

## What this repository contains

Only the **basic operating system** — the kernel of the Panpsychic
Cyborg Multitude — plus the networking architecture that connects
kernels into a fabric:

```
multitude.py                      entrypoint (python multitude.py ...)
PANPSYCHIC_CYBORG_MULTITUDE.md    manifesto + project description
NETWORKING_STACK.md               node-to-node networking architecture
                                  (zenoh fabric, namespace, events, policy)
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
                  proposal/vote envelopes, key namespace, typed events,
                  transport ABC, fail-closed policy, GET→POST bridge
  integrations/zenoh/          — Zenoh fabric transport (Phase 2)
  integrations/hermes/         — AI-agent integration (thin adapter)
  integrations/telegram/       — messaging transport (thin adapter)
```

No simulation. No scrapers. No experimental sensors. Just the
constitution: memory, voice, decision.

## Quick start

```bash
pip install pydantic   # the only dependency beyond the stdlib

python multitude.py found --name "My Multitude" --founder alice
python multitude.py say --as alice --text "The tribe is alive."
python multitude.py status
```

Optional node-to-node networking (Phase 2 fabric):

```bash
pip install eclipse-zenoh
export PCM_ZENOH_ENABLED=true
python3 -m unittest tests.test_pcm_phase2_zenoh   # two-node exchange demo
```

## Networking architecture

The full node-to-node networking design is documented in
[NETWORKING_STACK.md](NETWORKING_STACK.md): why chat infrastructure
(homeservers, rooms, accounts) was rejected for a distributed nervous
system, how the zenoh fabric carries signed envelopes between nodes
(humans, agents, devices, sensors), the `pcm/<domain>/<entity>/<resource>`
key namespace, the typed event vocabulary, and the fail-closed
authorization model.

Phases:

```text
Phase 0  DONE  kernel + did:key identity + signed PCM 1 envelopes
Phase 1  DONE  single node: proposal envelopes, status surface
Phase 2  DONE  fabric: namespace + events + Transport ABC + ZenohTransport
Phase 3  NEXT  two+ nodes end-to-end: VC capability grants, memory mirror
Phase 4       BCI/biosignal nodes over the same subjects
Phase 5       ecosystem interop (4CAT, LaclauGPT interchange, QDA exports)
```

## Documents

- [PANPSYCHIC_CYBORG_MULTITUDE.md](PANPSYCHIC_CYBORG_MULTITUDE.md) — manifesto + project description
- [NETWORKING_STACK.md](NETWORKING_STACK.md) — networking architecture (zenoh fabric)
- [LICENSE](LICENSE) — CC0 1.0 Universal