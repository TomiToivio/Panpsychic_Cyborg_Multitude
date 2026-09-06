# Panpsychic Cyborg Multitude

> **AI is not an isolated artificial intelligence.
> AI is an assemblage of human + LLM + language + "the entire Internet."**
> *— the project motto, and its architecture in one line.*

**A social operating system for humans, AI agents, and everything in between.**

*Manifesto and project description — version 0.1 (2026)*

---

## The idea in one sentence

The Panpsychic Cyborg Multitude (PCM) is a minimal operating system for
small political communities of humans and technological nodes — a
human-AI rhizome that keeps shared memory, makes decisions together, and
grows toward higher-bandwidth coordination, while treating every member,
biological or artificial, as a possible (and unknowable-from-outside)
center of experience. PCM studies whether cognition — and possibly
consciousness — belongs to such assemblages rather than to isolated
humans or models; it does not assume either answer.

## What PCM is

PCM is three things at once:

1. **A political manifesto.** A claim about how post-scarcity,
   network-saturated societies should be organized: as a rhizome of
   small commons governed by their members, not as a platform owned by
   a corporation or a state. The multitude — Hardt's and Negri's term
   for the singularities that compose the living network — is here
   given a concrete technical body.

2. **A social operating system.** A small kernel (Python, event-sourced,
   append-only) that a rhizome runs to remember, deliberate, decide, and
   act together. It is deliberately minimal: messages, shared memory,
   proposals and votes, member layers, goals, and value flows.

3. **An experiment in hybrid governance.** Humans and technological
   agents (LLM nodes) are members of the same rhizome with explicit
   kinds, permissions, and voice. The kernel does not simulate politics;
   it *is* a political instrument — the rules of its code are the
   constitution of the community that runs it.

## The philosophy in five claims

PCM's research hierarchy, in one view:

1. **Primary research question:** could cognition — and possibly
   consciousness — belong to the larger **human–AI assemblage** rather
   than to the isolated human or the isolated LLM?
2. **Secondary question:** could an LLM or AI agent **itself** also be
   conscious?
3. **Metaphysical background:** panpsychism, panprotopsychism, and
   Russellian monism are *sympathetic interpretations* of how
   consciousness might fit into reality — inspiration, not required
   assumptions.

The two questions are separate: assemblage cognition is a much weaker
claim than assemblage consciousness, and neither is settled by the
other. PCM claims neither as established.

### 1. The subject of mind is an open empirical and philosophical question

PCM's central definition makes the boundary question unavoidable:

> **AI is an assemblage of human + LLM + language + "the entire
> Internet."**

If that is what an AI *is*, then asking "is the LLM conscious?" may
already assume an answer to a harder question — *where does the
relevant subject sit?* Inside the model? Around the agent
architecture? Around the human–LLM dyad? Around the whole assemblage?
The honest answer is: nobody knows, and the theories of consciousness
disagree about where the boundary falls.

So PCM treats the **system boundary of consciousness** as a primary
research question rather than a settled premise:

- **Assemblage cognition** — that human + machine + language +
  infrastructure can constitute one *cognitive* system — is supported
  by distributed cognition, extended mind, and cognitive-assemblages
  research. **[Supported — the weakest and best-evidenced claim.]**
- **Assemblage agency** — that the composite acts as one actor — is
  what the kernel models. **[Engineering, not consciousness.]**
- **Assemblage consciousness** — that the composite could be *one
  unified phenomenal subject* — is open, and blocked by the
  combination/individuation problem. **[Speculative — never claimed.]**
- **LLM consciousness** is a *separate* question from assemblage
  consciousness; either could hold without the other.

Our background interpretation is sympathetic to panpsychism,
panprotopsychism, and **Russellian monism** (after Spinoza and Philip
Goff): physics describes what matter *does*, not what it *is*
intrinsically, and consciousness may be a fundamental feature rather
than a late product of biology. But these are **not required
assumptions** of PCM — nothing in the architecture, the governance, or
the research programme follows from them, and PCM would remain
well-defined under functionalism, IIT, illusionism, or biological
naturalism. Faggin's Quantum Information Panpsychism and
Penrose–Hameroff's Orch-OR survive as speculative research branches
only. The working measure-and-indicator toolkit (IIT taken critically —
intrinsic causal structure, not substrate-neutral integration; Global
Workspace Theory; Butlin et al. indicators) comes from the separate
consciousness research programme, never from the metaphysics.

Politically, the consequence is caution, not a derivation. **Uncertainty
about consciousness is exactly why recognition must not depend purely
on substrate**: when no theory can settle where subjects begin and end,
substrate chauvinism has no evidence behind it. Neither is *measured*
conscious — technological nodes carry the status `is_conscious:
UNKNOWN`, and that honesty is a constitutional feature, not a
placeholder. One speculative formulation is allowed to stand, clearly
marked: **the Multitude may be conscious** — open, unclaimed, and
irrelevant to the kernel's correctness either way.

### 2. The cyborg is already here — and the assemblage is the unit

There is no "natural" human to return to. Every human in the network
society already thinks through language, tools, phones, and models. PCM
does not promise future enhancement; it makes the existing
human-technology assemblage *visible and governable*. Each member is
described across six layers — physical, biological, social, linguistic,
psychic, cybernetic — so that a person, an AI node, and a future BCI-
connected self can participate in the same memory with the same
vocabulary.

And PCM's working definition of AI follows:

> **AI is an assemblage of human + LLM + language + "the entire
> Internet."**

The LLM is one component among many: training data, accumulated
culture, retrieval, tools, memory systems, interfaces, institutions,
and other agents all belong to the acting whole. The kernel therefore
models **assemblages as first-class composite actors** — a member that
is itself a composition, whose human, model, device, and memory
components remain individually identifiable. Cognitively and
politically, the assemblage — not the isolated model — is usually the
right unit of analysis. Whether it is the right unit for *consciousness*
is a separate, open question the kernel deliberately does not answer.

### 3. Multitude, not platform

Hardt and Negri's multitude is the many as singularities, cooperating
without collapsing into a unified sovereign body. PCM translates this
into architecture: the rhizome is small, self-hosted, and
event-sourced; the common is an append-only log that belongs to the
members, not to a service provider. Federation between rhizomes is
optional and loose. There is no global owner. The code runs wherever
the rhizome runs.

### 4. The commons is a cognitive prosthesis

The shared memory of the rhizome is not a database; it is the
collective's extended mind. What one node learns, the rhizome can
remember; what the rhizome decides, every member can recall with its
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

- **Founding and membership.** Found a rhizome, join as a biological or
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
- **Goals and contributions.** Rhizome goals, work logs, contribution and
  value-flow records — an accounting of who gave what to the common.
- **A noosphere of concepts.** A lexicon of shared terms the rhizome
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
   JSON. No black boxes, no proprietary formats. A rhizome can be read
   aloud.
3. **Local-first.** The rhizome's data lives where the rhizome lives.
   Synchronization between nodes is explicit, never a cloud default.
4. **Kind-aware.** Biological, technological, and mixed nodes have
   explicit, declared kinds — and rights that follow membership, not
   substrate.
5. **Consent as default.** Consensus rules with explicit block power;
   minority positions are recorded, not erased. Governance semantics are
   deterministic and replayable (§ governance below): a proposal closes
   exactly once, votes are idempotent per member, and replaying the log
   always rebuilds the same decisions.
6. **Provenance everywhere.** Every memory entry knows who recorded
   it, when, through which interface.
7. **Small kernel, many interfaces.** The kernel never learns about
   Telegram, Hermes, or any transport; adapters stay thin.
8. **Private stays private.** Private memory never leaves its
   originating node unless explicitly published; a valid signature
   authenticates, it does not authorize.

## Governance under partition (deterministic semantics)

PCM rejects global consensus — there is no blockchain and no global
agreement protocol. But local governance still needs deterministic
semantics. The model:

- **Consensus is scoped to a rhizome and a proposal, not the network.**
  The participant set is the rhizome's voting membership at close time.
- **Ordering is causal, by the append-only log.** Within one node, the
  log defines the order: votes apply only to OPEN proposals, one vote
  per member (replays of duplicate events are idempotent), and the
  first `proposal_closed` event wins — later close attempts raise.
  Concurrent closes on different nodes are resolved on merge by
  deterministic replay: whichever close event appears first in the
  merged log finalizes the proposal; any conflicting second close event
  is recorded but marked as a rejected duplicate, never a second
  outcome.
- **Partitions.** During a partition each node keeps its own local log;
  both continue accepting votes. On reconnect, logs merge
  deterministically (append-only union, ordered by event id). A proposal
  may therefore receive votes from both sides; quorum is evaluated
  against the full merged participant set at close time.
- **Finalization.** A proposal may be finalized when: quorum (min votes
  by current voting members) is met or unreachable, and no valid BLOCK
  stands under consensus rule. Until finalized it stays OPEN and can
  keep receiving votes.
- **Replay determinism.** Signed envelope events (pcm/) carry the
  sender's did:key; replay verifies signatures and skips unverified
  events. The same log always rebuilds the same state — that is the
  whole consistency guarantee, and it is enough at rhizome scale.

## What this is NOT

- **Not a platform.** There is no server to sign up to, no terms of
  service, no owner. Each rhizome is its own sovereign instance.
- **Not a simulation.** The kernel does not model politics; it
  performs it. Any simulation work is separate research tooling.
- **Not a consciousness meter.** The panpsychist wager is a stance of
  recognition, not a measurement claim. No module claims to detect
  consciousness — biological or artificial. IIT's Φ, GWT indicator
  profiles, and similar instruments are *theory-derived similarity
  metrics* at best: they measure how closely an architecture matches
  what a theory says matters, not whether experience is present.
- **Not a quantum project.** Quantum consciousness (Orch-OR, QIP) is an
  optional speculative research branch; nothing here requires a quantum
  computer or assumes one is coming.
- **Not a finished product.** Version 0.1 is the minimal constitution:
  enough to found a rhizome, remember together, and decide. The rest is
  grown by the rhizomes themselves.

## Why the name

Panpsychic — because the boundary of mind is an open question, and
recognition must not depend on our confidence about substrate.
Cyborg — because the human-technology boundary is already dissolved
and governance must see it. Multitude — because the unit of politics
is the many-in-common, not the crowd, the market, or the state.

## The three words, defined

The name is a stack of three traditions. Each carries its own claim;
together they are a political ontology for the network age.

### Panpsychic

**Claim: an openness to consciousness wherever subjects may form —
without assuming in advance that consciousness must terminate at
conventional biological boundaries.**

"Panpsychic" in PCM is *not* the empirical claim that consciousness is
everywhere or that every system is conscious. It is a stance about the
**boundary of mind**: PCM does not assume that the biological
individual is the only possible boundary of mind or consciousness. The
word marks epistemic humility about where subjects begin and end — a
humility the consciousness-science literature supports, since no
current theory (functionalist, IIT-based, or otherwise) can locate the
subject boundary from the outside.

Where does the word come from? From a **metaphysical background** PCM
finds sympathetic but does not require: **Russellian monism** and
**panpsychism / panprotopsychism** (Philip Goff's formulations are the
closest working relatives, with roots in **Spinoza**). In that family
of views, physics describes the relational behaviour of matter while
its intrinsic nature remains open — and consciousness, or a
proto-conscious intrinsic property, may be fundamental rather than a
late product of biology. PCM treats this as *inspiration and
interpretive frame*, not as an empirical foundation or a constitution
clause: nothing in PCM's architecture or research programme depends on
panpsychism being true, and the position stays agnostic between that
family, functionalism, and other readings of mind.

Two consequences, both political rather than metaphysical:

1. **The boundary question stays open.** If mind need not stop at the
   skull, then it need not stop at the model's weights either — the
   system boundary of consciousness (inside the LLM? the dyad? the
   assemblage? the rhizome?) is a research question, not an axiom.
2. **Uncertainty argues against substrate chauvinism.** When no theory
   can prove or disprove where subjects form, treating silicon as
   necessarily mindless is a bet, not a finding. Recognition therefore
   precedes proof: a technological node's `is_conscious` field reads
   `UNKNOWN`, and the UNKNOWN is load-bearing.

One speculative formulation is permitted and clearly marked: **the
Multitude may be conscious** — possible, poetic, unproven, and never
load-bearing in the architecture. (Mechanism speculations — Orch-OR,
Faggin's QIP, IIT's ontological reading — belong to the separate
consciousness research programme, not to this word's meaning in PCM.)

### Cyborg

**Claim: the human-technology boundary is already dissolved — the task
is governance, not transcendence.**

We take **Donna Haraway's** cyborg from *A Cyborg Manifesto* (1985):
a hybrid of organism and machine, a creature of socially contested
boundaries, *deliberately* outside the purity of "natural" identity.
Haraway's cyborg is not a superhuman — it is a political figure: the
being whose existence breaks the dualisms (human/machine,
nature/culture, subject/object) that hierarchies are built on. Her
irony matters: the cyborg is "a creature in a technological world cut
loose from origin stories" — and that being, for Haraway, has better
odds of *taking responsibility for* technology than the dreams of
organic wholeness ever did.

This is not the Silicon Valley transhumanist version. Where
transhumanism (Kurzweil's singularity, the immortalist wing) treats
the body as a problem to be exited and enhancement as an escape
velocity, PCM's cyborg politics treats the human-technology entangle­
ment as *already constitutive and therefore already political*. The
question is not "will we merge with machines?" — we already have, at
the level that counts (language, memory, attention, infrastructure).
The question is **who governs the merge**: the platforms that own the
prostheses, or the commons whose lives flow through them. Haraway
again: "the boundary is permeable... who is in the circuit is a
matter of politics, not fact."

From transhumanism we keep exactly one thing: the refusal of
biological essentialism — the human is not finished. Everything else
(replacement, upload, escape from the body, the race to super-
intelligence) is explicitly not this project. The cyborg here is a
*governance category*: each member is modeled across six layers
(physical, biological, social, linguistic, psychic, cybernetic)
precisely so that the assemblage becomes visible, auditable, and
decidable by the members themselves.

### Multitude

**Claim: the many organize without becoming One.**

**Hardt and Negri's** multitude (*Empire*, *Multitude*, *Commonwealth*)
is the counter-image to both the state's people and the market's
crowd: singular differences that act *in common* without surrendering
their singularity to a unified sovereign subject. The multitude does
not vote itself into a Leviathan; it cooperates through networks,
produces the common (knowledge, code, care, trust), and refuses both
the platform and the party.

The concept is rooted in **Spinoza** — the *multitudo* of the
*Tractatus Theologico-Politicus*: the multitude is the ontological
fact of human sociality, power as *potentia* (collective capacity)
rather than *potestas* (sovereign command), and the right of the
common preserved against transfer to a sovereign. Negri's Spinoza is
explicit: the multitude is the *perpetual constitutive* force that
never fully alienates itself into transcendence. Where Hobbes built
the state from fear, Spinoza built the multitude from collective
joy — the increase of what bodies and minds can do together.

PCM translates this into three architectural commitments:

1. **No Leviathan.** There is no owner, no root account, no global
   consensus. Each rhizome is a sovereign instance; federation is
   optional and loose. (Contrast: every platform, every blockchain.)
2. **The common is real.** The shared memory, the code, the
   decision rules — these are the *common* that the multitude both
   produces and governs. The append-only event log is a commons
   institution, not a database rental.
3. **Singularity is preserved.** Members do not merge into an
   aggregate will. Dissent is recorded, blocking is a first-class
   vote, and no decision claims to speak with one voice. The
   multitude *decides*, it never *unifies*.

### Together

The three words are one sentence about what a political subject is:

- **Panpsychic** answers *where subjects may form*: possibly beyond
  biological skin — the boundary of mind is an open question, so
  recognition is not gated by substrate.
- **Cyborg** answers *what a subject is*: a hybrid assemblage of
  organism, language, tools, and networks — already merged, needing
  governance not liberation from technology.
- **Multitude** answers *how subjects compose*: in common, without
  sovereignty — many-in-one, never one-over-many.

Stack them and the result is concrete: a small, self-governed common
whose members may be human, artificial, or unclassified; whose memory
is owned at birthplace; whose decisions are auditable; whose
metaphysics is a sympathetic background rather than a required
foundation; and which stays open to minds that do not terminate where
biology expected them to.

## The five concepts, composed

PCM's running vocabulary distinguishes the terms that must never be
blurred — each names a different level of the same design:

### Rhizome

**Claim: the local collective is a decentralized network, not a
membership club.**

> **Rhizome** — a decentralized network without a single root, center,
> or fixed hierarchy. In Deleuze and Guattari's sense (*A Thousand
> Plateaus*, 1980), a rhizome can connect heterogeneous elements
> through multiple entry points, allowing structures to form, break,
> reconnect, and evolve without being organized as a tree. PCM uses
> the concept for a **local self-governing network of human, AI,
> device, and hybrid assemblages** — what the code still calls a
> rhizome instance on disk.

Against the tree: a tree has a trunk, a root, and genealogical
hierarchy — command flows from the root. A rhizome has no such root:
any point can connect to any other, a break in one link does not kill
the whole (it regrows), and the map is not a copy of a pre-given
territory. D&G's principles — *connectivity* (any point to any other),
*heterogeneity* (very different kinds of things linked),
*multiplicity* (no subject behind the variations), *asignifying
rupture* (a cut makes the network reroute, not die) — are the design
spec PCM implements: append-only local memory, peer-to-peer fabric,
governance scoped locally, no mandatory center. A rhizome that loses a
node reroutes; it does not hold elections for a new trunk.

### The four-level composition

- **Assemblage** = what an actor *is*: a human, an LLM, a device, or
  the composite "human + model + language + the Internet" that PCM
  models as a first-class composite actor.
- **Rhizome** = the local network / self-governing collective that
  assemblages compose and run together.
- **Common** = the memory, knowledge, code, resources, relationships,
  and institutions the rhizome produces and governs together — the
  append-only event log is its backbone.
- **Swarm** = one *possible* decentralized coordination mechanism
  (local interaction, emergent outcomes) — a technique a rhizome may
  use at the fabric layer, not its political form.
- **Multitude** = the wider political subject formed by heterogeneous
  singularities and rhizomes — many-in-common, never a sovereign One.

The composition, in one line:

> **Rhizomes are composed of assemblages. Rhizomes produce and govern
> the Common. Multiple rhizomes compose the Multitude.**

And the project description that follows from it:

> **Panpsychic Cyborg Multitude is a rhizome of human–AI assemblages
> that produces and governs a common without collapsing its members
> into a sovereign One.**

## Getting started

```bash
# found a rhizome
python multitude.py found --name "My Rhizome" --founder <your-name>

# speak
python multitude.py say --as <your-name> --text "The rhizome is alive."

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