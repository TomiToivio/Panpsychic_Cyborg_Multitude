# Panpsychic Cyborg Multitude

**A social operating system for humans, AI agents, and everything in between.**

*Manifesto and project description — version 0.1 (2026)*

---

## The idea in one sentence

The Panpsychic Cyborg Multitude (PCM) is a minimal operating system for
small political communities of humans and technological nodes — a
human-AI tribe that keeps shared memory, makes decisions together, and
grows toward higher-bandwidth coordination, while treating every member,
biological or artificial, as an unknown and unmeasurable center of
experience.

## What PCM is

PCM is three things at once:

1. **A political manifesto.** A claim about how post-scarcity,
   network-saturated societies should be organized: as a rhizome of
   small commons governed by their members, not as a platform owned by
   a corporation or a state. The multitude — Hardt's and Negri's term
   for the singularities that compose the living network — is here
   given a concrete technical body.

2. **A social operating system.** A small kernel (Python, event-sourced,
   append-only) that a tribe runs to remember, deliberate, decide, and
   act together. It is deliberately minimal: messages, shared memory,
   proposals and votes, member layers, goals, and value flows.

3. **An experiment in hybrid governance.** Humans and technological
   agents (LLM nodes) are members of the same tribe with explicit
   kinds, permissions, and voice. The kernel does not simulate politics;
   it *is* a political instrument — the rules of its code are the
   constitution of the community that runs it.

## The philosophy in five claims

### 1. Panpsychism as a political ontology

Mind is not a rare accident of biology. We adopt a panpsychist working
model (after Spinoza's ethics, Faggin's Quantum Information Panpsychism,
and Levin's Technological Approach to Mind): every substrate may host
some form of experience. Politically, this means no member of a
multitude is *in principle* excluded from recognition by its substrate.
A human is not privileged by being made of neurons; an AI is not
excluded by being made of silicon. Neither is *measured* conscious —
technological nodes carry the status `is_conscious: UNKNOWN`, and that
honesty is a constitutional feature, not a placeholder.

### 2. The cyborg is already here

There is no "natural" human to return to. Every human in the network
society already thinks through language, tools, phones, and models. PCM
does not promise future enhancement; it makes the existing
human-technology assemblage *visible and governable*. Each member is
described across six layers — physical, biological, social, linguistic,
psychic, cybernetic — so that a person, an AI node, and a future BCI-
connected self can participate in the same memory with the same
vocabulary.

### 3. Multitude, not platform

Hardt and Negri's multitude is the many as singularities, cooperating
without collapsing into a unified sovereign body. PCM translates this
into architecture: the tribe is small, self-hosted, and
event-sourced; the common is an append-only log that belongs to the
members, not to a service provider. Federation between tribes is
optional and loose. There is no global owner. The code runs wherever
the tribe runs.

### 4. The commons is a cognitive prosthesis

The shared memory of the tribe is not a database; it is the
collective's extended mind. What one node learns, the tribe can
remember; what the tribe decides, every member can recall with its
provenance. This is the practical answer to Castells' network society:
power flows through communication networks, so the networks themselves
must be owned and governed by those whose lives flow through them.

### 5. Governance is the technology

Votes, proposals, consent rules, contribution records, value flows —
these are not UI chrome around the "real" system. They *are* the
system. Every decision the community makes is recorded as an immutable
event, so governance is auditable the way a blockchain is auditable,
but human-scale: consent-first, with explicit block power and
quorum rules the members choose.

## What the minimal OS does

The kernel in `src/multitude/` is deliberately small. It provides:

- **Founding and membership.** Found a tribe, join as a biological or
  technological node, promote/demote voices.
- **The stream.** Members speak; every message is an event.
- **Shared memory.** Typed, tagged, provenance-bearing memory entries
  (`remember`, `search`), plus private local notes per member that can
  be published deliberately.
- **Decisions.** Proposals with configurable rules (consensus,
  majority, unanimity), votes including explicit *block*, tallies,
  and recorded decisions.
- **Member layers.** The six-layer profile of every node, updated by
  self-reports or observations, all appended as events.
- **Goals and contributions.** Tribe goals, work logs, contribution and
  value-flow records — an accounting of who gave what to the common.
- **A noosphere of concepts.** A lexicon of shared terms the tribe
  defines as it works.
- **Technological nodes.** LLM agents join as full members (`counsel`
  lets a node speak in the stream), with the same log, the same
  transparency.
- **Interfaces.** A CLI today; a local HTTP API; messaging-platform
  adapters are thin transport layers, never the kernel itself.

That is the whole operating system. No simulation, no scraping, no
experimental sensors — those live in separate research repositories.
The kernel is what a community needs to *exist* as a governed common:
memory, voice, decision.

## Design principles

1. **Event-sourced.** Everything that happens is an immutable event;
   state is always replayable. History belongs to the members.
2. **Human-readable first.** Events and memory are plain JSONL and
   JSON. No black boxes, no proprietary formats. A tribe can be read
   aloud.
3. **Local-first.** The tribe's data lives where the tribe lives.
   Synchronization between nodes is explicit, never a cloud default.
4. **Kind-aware.** Biological, technological, and mixed nodes have
   explicit, declared kinds — and rights that follow membership, not
   substrate.
5. **Consent as default.** Consensus rules with explicit block power;
   minority positions are recorded, not erased.
6. **Provenance everywhere.** Every memory entry knows who recorded
   it, when, through which interface.
7. **Small kernel, many interfaces.** The kernel never learns about
   Telegram, Hermes, or any transport; adapters stay thin.

## What this is NOT

- **Not a platform.** There is no server to sign up to, no terms of
  service, no owner. Each tribe is its own sovereign instance.
- **Not a simulation.** The kernel does not model politics; it
  performs it. Any simulation work is separate research tooling.
- **Not a consciousness meter.** The panpsychist wager is a stance of
  recognition, not a measurement claim. No module claims to detect
  consciousness — biological or artificial.
- **Not a finished product.** Version 0.1 is the minimal constitution:
  enough to found a tribe, remember together, and decide. The rest is
  grown by the tribes themselves.

## Why the name

Panpsychic — because recognition must not depend on substrate.
Cyborg — because the human-technology boundary is already dissolved
and governance must see it. Multitude — because the unit of politics
is the many-in-common, not the crowd, the market, or the state.

## Getting started

```bash
# found a tribe
python multitude.py found --name "My Tribe" --founder <your-name>

# speak
python multitude.py say --as <your-name> --text "The tribe is alive."

# remember
python multitude.py remember --as <your-name> --title "First memory" --text "..."

# propose and decide
python multitude.py propose --by <your-name> --title "..." --text "..." --rule consensus
python multitude.py vote --as <your-name> --proposal <id> --position for
python multitude.py close --by <your-name> --proposal <id>

# status
python multitude.py status
```

Requires Python 3.11+ and `pydantic`. Everything else is standard
library.

## License

CC0 1.0 Universal. The common is common: use it, fork it, found your
own multitude. Attribution appreciated, never required.

## Source and project

This minimal distribution mirrors the kernel of the Panpsychic Cyborg
Multitude project. The full research environment (agents, BCI
experiments, simulation studies) develops separately and is not part
of this public core.

*Panpsychic Cyborg Multitude — the social operating system of the
many-as-one and the one-as-many.*