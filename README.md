# Panpsychic Cyborg Multitude — minimal public distribution

**PCM is a social operating system for human-AI tribes: shared memory,
deliberation, decisions, and member layers — event-sourced, local-first,
CC0.**

Read the manifesto: [PANPSYCHIC_CYBORG_MULTITUDE.md](PANPSYCHIC_CYBORG_MULTITUDE.md)
— the philosophy and the project description in one document.

## What this repository contains

Only the **basic operating system** — the kernel of the Panpsychic
Cyborg Multitude:

```
multitude.py                      entrypoint (python multitude.py ...)
PANPSYCHIC_CYBORG_MULTITUDE.md    manifesto + project description
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
                  proposal/vote envelopes, GET→POST bridge (dormant)
  interfaces/web.py            — local HTTP API
  integrations/hermes/         — AI-agent integration (thin adapter)
  integrations/telegram/       — messaging transport (thin adapter)
  integrations/matrix/         — Matrix transport skeleton (read-only, dormant)
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

See the manifesto for the full command set (memory, proposals, votes,
layers, goals).

## The six-layer agent model

Every agent in the Multitude — human, machine, or cyborg — is described
along the same six layers. A node is not a row in a database; it is a
being with a body, a mind, a language, and a network link, and the
kernel models all of it:

| Layer | What it describes |
|---|---|
| **Physical** | Location in space, environment — where the node *is* |
| **Biological** | Flesh and its needs: sleep, hunger, mood — the ape in human agents |
| **Psychic** | The psyche of conscious agents (Quantum Information Panpsychism as the working model) |
| **Linguistic** | Languages spoken, vocabularies known |
| **Social** | The tribe, wider networks and systems around the node |
| **Cybernetic** | Connection to the network: interface mode, links, runtime — text today, BCI eventually |

The layers make human and technological members commensurable: both are
profiled with the same vocabulary, in the same event log. Each layer
state is a `layer_recorded` event — replaying the log rebuilds every
agent's profile, so history belongs to the members, never to the
platform. Records are self-reported by default; other members may
observe and report a node's layers (`reported_by`), and unknown fields
are rejected so the shared vocabulary stays clean.

## Principles

- Event-sourced and replayable — history belongs to the members.
- Local-first — the tribe's data lives with the tribe.
- Kind-aware membership — biological and technological nodes, same log.
- Consent-first governance with explicit block power.
- Thin adapters, small kernel — transports never touch the core.

## License

CC0 1.0 Universal — the common is common.