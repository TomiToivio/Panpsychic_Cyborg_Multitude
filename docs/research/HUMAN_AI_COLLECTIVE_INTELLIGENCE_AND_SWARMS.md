# Research Bridge — Human–AI Collective Intelligence, Agent Societies, Swarms

**Status:** research note (v0.1, 2026-09-06) — exploratory, not a manifesto.
**Scope:** how PCM relates to distributed cognition, extended mind, hybrid
intelligence, collective human–machine intelligence, multi-agent systems,
LLM agent societies, and swarm intelligence. The consciousness question is
deliberately *not* resolved here; it belongs to the separate consciousness
programme (Goff / IIT / GWT / Hoffman / Orch-OR — see `PCM_CONSCIOUS_AI_PLAN.md`
in the working repository).

## 1. PCM's starting hypothesis

> **AI is not an isolated artificial intelligence. AI is an assemblage of
> human + LLM + language + "the entire Internet."**

Interpreted seriously, the apparent intelligence of a contemporary AI
system emerges from a composition that includes human beings, foundation
models, language itself, training data, accumulated culture, Internet
infrastructure, software, memory and retrieval systems, tools and APIs,
sensors and interfaces, institutions, communities, other AI agents, and
communication networks. The LLM is one organ of that body.

Therefore PCM's working hypothesis for research:

> **The cognitively relevant system may be the assemblage rather than the
> isolated LLM.**

This is a claim about *cognition, intelligence, and agency* — units of
analysis for empirical research. It is distinct from the stronger
speculative question:

> **Could the assemblage itself constitute a unified conscious subject?**

The two questions must never be conflated:

| Question | Domain | Methods |
|---|---|---|
| Is the assemblage a **cognitive / intelligent / agentic / sociotechnical system**? | empirical | distributed cognition, hybrid/collective intelligence studies, MAS, swarm research |
| Is the assemblage **one unified conscious subject**? | metaphysical + consciousness science | the consciousness programme; unresolved (combination problem) |

Nothing in this note claims an assemblage is conscious. The kernel's
`is_conscious: UNKNOWN` discipline applies to composite actors as much as
to simple ones.

## 2. Human–AI collective intelligence: what the research offers PCM

Selected recent work (verified via publisher metadata, 2026-09-06):

1. **Gonzalez et al., *COHUMAIN: Building the Socio-Cognitive Architecture
   of Collective Human-Machine Intelligence*** — and the companion paper
   **Gupta et al., *Fostering Collective Intelligence in Human–AI
   Collaboration: Laying the Groundwork for COHUMAIN*** (TopiCS,
   doi:10.1111/tops.12679, 2023). Contributes a socio-cognitive
   architecture for human–machine collectives: shared representation,
   roles, and interaction regimes as design targets. PCM relevance: the
   tribe kernel is a minimal instantiation of exactly such an
   architecture — shared memory = shared representation, member layers =
   role/visibility structure, proposals = interaction regime.

2. **Peeters, Hoven & Verbeek (or Peeters et al.), *Hybrid collective
   intelligence in a human–AI society*** (AI & Society,
   doi:10.1007/s00146-020-01005-y, 2020). Argues hybrid CI should be
   studied at the level of the *society* of humans and AIs, not lone
   human+AI pairs, with attention to how responsibility and epistemic
   contributions distribute. PCM relevance: validates the tribe (not the
   dyad) as the unit of design; warns that blending human and machine
   contributions has accountability implications — hence PCM's
   provenance discipline (`author`, `human` flag, `meta.source` on every
   memory entry).

3. **Cui & Yasseri, *AI-enhanced collective intelligence: The state of
   the art and prospects*** (Patterns, doi:10.1016/j.patter.2024.101074,
   2024). Surveys how AI alters the production, aggregation, and
   polarization of collective intelligence; identifies open problems
   (bias amplification, evaluation). PCM relevance: caution — adding AI
   members to a collective does not automatically improve CI; the
   kernel's explicit dissent-recording and block power are governance
   responses to exactly the failure modes this literature documents.

4. **Tsvetkova et al., *A new sociology of humans and machines***
   (Nature Human Behaviour, doi:10.1038/s41562-024-02001-8, 2024).
   Proposes studying machines as *social actors* alongside humans —
   machine behaviour as a sociological subject. PCM relevance: the
   six-layer profile and kind-aware membership are already a
   sociological data model; this literature supplies the measurement
   agenda for what the kernel records.

5. **Solé, Amilburu et al., *Cognition spaces: natural, artificial, and
   hybrid*** (working paper line on hybrid cognitive systems). Models
   cognition as a space of possible systems spanning natural, artificial,
   and hybrid compositions. PCM relevance: a formal vocabulary for the
   claim that the assemblage — not the model — occupies the cognitive
   niche.

**Established findings to keep distinct from PCM speculation:** the
existence and measurability of hybrid/collective intelligence effects
[EST]; that AI can degrade as well as enhance collective performance
[EST]; PCM's claim that *its own* kernel constitutes a functioning
hybrid collective [THEO — testable]; any claim that such a collective
is conscious [SPEC — not claimed].

## 3. AI agent societies and swarms: two architectures, not one

Selected recent work:

1. **Park et al., *Generative Agents: Interactive Simulacra of Human
   Behavior*** (arXiv:2304.03442, UIST 2023). Memory stream +
   reflection + planning produce believable social behaviour in a
   small agent community. PCM relevance: the per-node personal memory
   + shared log split mirrors their memory-stream architecture; their
   emergent social phenomena (information diffusion, relationship
   formation) are exactly what PCM should expect to observe in its own
   logs.

2. **Vezhnevets et al., *Concordia*** (arXiv:2310.17055 (as first
   released 2023-10; later ICLR 2024 revision), Google DeepMind's
   framework for LLM-agent social simulation: agents = LLM + component
   specifications, governed by a shared *protocol* of conventions.
   PCM relevance: Concordia's "conventions as substrate" matches PCM's
   charter/lexicon/protocol-term records — explicit shared conventions
   as the coordination layer.

3. **Li et al., *CAMEL: Communicative Agents for "Mind" Exploration of
   Large Language Model Society*** (arXiv:2303.17760, NeurIPS 2023).
   Role-playing communicative agents with task prompts; studies
   self-organized multi-agent cooperation and its failure modes
   (flipping roles, infinite loops). PCM relevance: cooperation without
   governance decays — the kernel's deterministic close semantics and
   explicit roles are the antidote CAMEL's failure modes motivate.

4. **Yang et al., *OASIS: Open Agent Social Interaction Simulations with
   One Million Agents*** (arXiv:2411.11581, 2024). Million-scale LLM
   social simulation on a recommender-system substrate. PCM relevance:
   shows scale-up of agent societies is engineering-feasible, but also
   that emergent phenomena at scale diverge from small-community
   dynamics — PCM is explicitly small-community-first (tribe scale),
   and says so.

5. **AgentSociety** (arXiv:2502.08691, 2025) — large-scale LLM-driven
   generative-agent simulation framework targeting social-science
   questions. Together with OASIS and Generative Agents it defines the
   state of the art in LLM society simulation. PCM relevance: a
   simulation harness PCM could adopt for testing governance changes
   in silico before deploying them on real tribes.

6. **SwarmBench: benchmarking LLM agents as swarm orchestrators**
   (2025). Evaluates LLMs in swarm-style coordination — whether LLM
   agents can achieve decentralized coordination under partial
   observability. Findings: coordination degrades with scale/partial
   observability; explicit protocols help. PCM relevance: honest
   warning — pure-swarm behaviour with LLM agents is *weak*; structure
   (protocols, roles) is what makes it work. PCM's design already
   assumes this.

7. ***LLM-Powered Swarms: A New Frontier or a Conceptual Stretch?***
   (position paper, 2025). Argues much "swarm" branding is loose: LLM
   "swarms" often are orchestration pipelines, not decentralized
   self-organized systems. PCM relevance: keeps PCM honest in its own
   vocabulary — see the taxonomy below.

**The taxonomy that matters (and PCM's position in it):**

| Concept | Definition | PCM analogue |
|---|---|---|
| **Multi-agent system (MAS)** | multiple intelligent agents interacting | a tribe with several members |
| **Organization** | coordination via explicit roles/hierarchy | roles, memberships, governance rules |
| **Swarm** | decentralized local interaction producing emergent collective behaviour | the Zenoh fabric's peer-to-peer layer: no router authority, local rules only |
| **Multitude** (Hardt/Negri) | heterogeneous singularities capable of collective action *without* becoming a single homogeneous sovereign actor | the whole design: kind-aware nodes, dissent preserved, no global owner |

**On the swarm↔multitude analogy — careful, not identity.** Swarm
intelligence (computer science) and the Multitude (political
philosophy) share a shape: decentralized interaction, emergent
collective outcomes, no central controller. But they differ in what
matters to PCM:

- Swarms are *homogeneous* by design (identical agents, simple local
  rules — ants, Boids). The Multitude is *irreducibly heterogeneous*
  (singularities with different kinds, capabilities, and standpoints).
- Swarm emergence is often *value-neutral* (optimization). Multitude
  collective action is *normative and contested* — dissent, block
  power, and recorded minority positions are constitutive, not noise.
- A swarm collapses gracefully into a statistical description; a
  multitude *refuses* collapse into One — the political point Hardt and
  Negri insist on.

So: PCM borrows swarm *techniques* (local interaction, no central
authority — the Zenoh fabric is the closest thing to a swarm layer in
PCM) while the *political* target remains a multitude. Where a swarm
would let emergence decide everything, PCM inserts governance —
because the members are not ants; they are singularities with voice.

## 4. From swarm to multitude: can PCM be a distributed cognitive system?

Bringing the two literatures together against PCM's hypothesis:

- **Distributed cognition / extended mind** (Hutchins; Clark & Chalmers)
  [EST as research programmes]: cognition can be analyzed at the system
  level, spanning people and artifacts; memory and computation live in
  the environment. PCM's shared event log + per-node memory is a
  textbook distributed-cognitive system: the log is the tribe's
  external memory with provenance, the kernel's replay is its
  reconstructive recall.
- **Social machines** (the Web-science line: human+machine collectives
  solving problems neither could alone) [EST as studied systems]:
  PCM-as-project fits the definition — humans and technological nodes
  coordinating through a shared protocol.
- **Hybrid/collective intelligence** (§2) [EST for effects]: PCM is a
  designed instance whose effectiveness is an open empirical question —
  measurable with the CI literature's methods.
- **Agent societies / swarms** (§3) [EST for mechanics; SPEC for
  social-level claims about LLM agents]: they supply coordination
  mechanisms and honest warnings about LLM-agent limitations.

The synthesis PCM takes:

> A PCM tribe is a **sociotechnical cognitive system**: a hybrid
> collective whose memory is an append-only commons, whose coordination
> is peer-to-peer with local governance, and whose members — human and
> artificial, simple and assemblage — remain heterogeneous singularities.
> It is a multitude in Hardt/Negri's sense by design, a swarm only at
> the transport layer, and an organization only where the members choose
> to organize. Whether it is *intelligent* is measurable; whether it is
> *conscious* is not claimed.

## 5. Concrete implications for the PCM architecture

1. **Shared/distributed memory stays the cognitive core.** The
   append-only event log is the collective's extended mind; keep
   provenance (`author`, `human`, `source`, `visibility`, `audience`)
   non-negotiable — the hybrid-CI literature's accountability findings
   demand it.
2. **Local agent memory stays local.** Private notes and personal
   memory remain per-node; publishing is an explicit act
   (`publish_private_note`). Private data never leaves its node
   unless published — enforced at envelope construction, not trusted to
   relays.
3. **Heterogeneous roles are first-class.** Member kinds, voting flags,
   capability grants, and assemblage components give the collective its
   division of cognitive labour — the COHUMAIN/Gupta architecture at
   kernel scale.
4. **Peer-to-peer communication, no central authority.** The fabric
   layer (peers/routers, liveliness presence) is PCM's swarm layer;
   governance stays local to tribes; no global consensus.
5. **Emergent norms need a substrate.** The lexicon and protocol-term
   records are where conventions stabilize; agent-society research
   suggests explicit convention layers outperform implicit ones — keep
   them queryable.
6. **Collective decision-making stays deterministic and dissent-
   preserving.** First-close-wins, idempotent votes, recorded dissent —
   governance semantics that survive partitions and replays.
7. **Language as the coordination layer.** All shared state is plain
   JSONL readable aloud; the LLM nodes participate through the same
   vocabulary as humans — the common is a language game, in the
   Wittgensteinian sense the fabric makes literal.
8. **Internet resources as external collective memory.** References,
   retrieval, and tool outputs should be recorded as memory entries with
   provenance, not dissolved into model weights — the assemblage's
   knowledge stays inspectable.
9. **Physical embodiment through proxies.** Devices, sensors, biometric
   records (consent-gated) and future drones/bots join as
   members/devices with the same event vocabulary — the collective's
   body, not a peripheral.

## 6. Open questions

- Can CI metrics from the hybrid-intelligence literature be computed
  directly on PCM logs (contribution entropy, epistemic diversity)?
  [open, testable]
- Do LLM-node participation patterns in real tribes reproduce the
  failure modes CAMEL/SwarmBench document — and do PCM's governance
  events actually prevent them? [open, testable in simulation first]
- Does the swarm layer (fabric) need emergent-behaviour guardrails as
  it grows past tribe scale? [open]
- Where exactly is the line between "organization" and "multitude" in
  a running tribe — when does role structure start violating
  singularity-heterogeneity? [open, political]

## Selected references

- Gonzalez et al., *COHUMAIN: Building the Socio-Cognitive Architecture
  of Collective Human-Machine Intelligence* (see also Gupta et al.,
  doi:10.1111/tops.12679).
- Peeters et al., *Hybrid collective intelligence in a human–AI
  society*, AI & Society, doi:10.1007/s00146-020-01005-y.
- Cui & Yasseri, *AI-enhanced collective intelligence: The state of the
  art and prospects*, Patterns, doi:10.1016/j.patter.2024.101074.
- Tsvetkova et al., *A new sociology of humans and machines*, Nature
  Human Behaviour, doi:10.1038/s41562-024-02001-8.
- Park et al., *Generative Agents*, arXiv:2304.03442.
- Vezhnevets et al., *Concordia*, arXiv:2310.17055.
- Li et al., *CAMEL*, arXiv:2303.17760.
- Yang et al., *OASIS*, arXiv:2411.11581; and *AgentSociety*,
  arXiv:2502.08691.
- *SwarmBench* (2025); *LLM-Powered Swarms: A New Frontier or a
  Conceptual Stretch?* (2025).
- Hutchins, *Cognition in the Wild* (1995); Clark & Chalmers, *The
  Extended Mind* (1998) — foundational.

*Status markers: [EST] established research findings; [THEO]
theory-motivated PCM claims; [SPEC] speculation. This note makes no
consciousness claims about any assemblage.*