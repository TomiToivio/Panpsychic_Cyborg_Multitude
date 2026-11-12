# The Cyborg Assemblage

**Operational companion to [`ONTOLOGY.md`](ONTOLOGY.md), specified by issue #91 §3.**

> **CYBORG = HUMAN + LLM + LANGUAGE + INTERNET**

This is a **model of extended and collective cognition**, not a claim that a present-day LLM is
conscious, an autonomous political subject, or a member with standing of its own. Every claim below
carries a register, and §6 gives each hypothesis the result that would count against it.

---

## 1. The four terms

| Term | What it contributes | What it does *not* contribute | Its characteristic failure |
| --- | --- | --- | --- |
| **HUMAN** | Embodied experience, intention, goals, accountability, situated judgement | Immunity from bias, or a stable "natural" cognition underneath the tool | Deskilling; outsourcing judgement; mistaking fluency for understanding |
| **LLM** | Linguistic transformation, pattern synthesis, retrieval-mediated reasoning support, generation | Grounding in the world; memory of its own errors; accountability | Hallucination; sycophancy; homogenisation of style and framing |
| **LANGUAGE** | Shared signs, external memory, discursive articulation, coordination | A guarantee that shared signs are shared meanings | Semantic drift; jargon as gatekeeping; untranslatable concepts treated as equivalent |
| **INTERNET** | Distributed archives, infrastructure, institutions, networks, platform control, feedback | Equal access; neutrality; persistence | Concentration, surveillance, platform decay, link rot, echo chambers |

The model is deliberately additive rather than emergent-by-assertion: each term adds something
identifiable, and the *system-level* claim — that the assemblage can do what no term does alone — is
what §3 tests.

## 2. Agency boundaries

Where the assemblage acts, and who answers for it:

1. **Agency is attributed, not discovered** (philosophical). PCM attributes agency to an assemblage
   when its behaviour is better predicted by treating the assemblage as the unit. That is a modelling
   decision, not a metaphysical discovery.
2. **Accountability does not distribute** (interpretive). When the assemblage acts, the humans remain
   answerable. "The model did it" is not an accountability transfer, and PCM's governance treats it
   as a failure of the assemblage's design.
3. **The LLM is not a psychic system** (philosophical). Under Luhmann's distinction, an LLM is not a
   consciousness and not a communication system: it transforms text. Whether it has experience is
   exactly the question PCM keeps open, not a premise it may assume.
4. **The network is not a mind** (philosophical). Distributed processing is not distributed
   experience. Nothing in the model licenses "the internet thinks".
5. **Extension is a claim, not a default** (empirical). A tool being present does not extend
   cognition. Extension means the task is performed differently *because* the coupling carries part of
   the work — which is measurable (§3).

## 3. Hypotheses and comparative designs

Each hypothesis is stated so that a result could count against it.

### H1 — Individual extension (empirical)
*Claim:* a human + LLM performs some cognitive tasks better than the human alone, controlling for
time and access to sources.

*Design:* human alone vs human + LLM vs human + LLM + networked sources; same tasks, fixed time
budget, randomised order, pre-registered outcome measures. *Disconfirming result:* no improvement, or
improvement that vanishes when time is equalised — the latter would suggest the effect is speed, not
extension.

### H2 — Collective intelligence (empirical)
*Claim:* groups with mediated shared language, network access and LLM assistance coordinate better
than groups without, on tasks with a measurable correctness or quality criterion.

*Design:* 2×2×2 factorial (shared language / network / LLM), same task, same group sizes, blind
scoring. *Disconfirming result:* no effect, or an effect explained entirely by one member's
individual performance.

### H3 — Language as constitutive (interpretive + empirical)
*Claim:* shared language does not merely transmit pre-existing positions; it shapes which positions
become articulable.

*Design:* compare the demand space that appears in monolingual vs bilingual coordination on the same
problem; code for demands that exist in one and not the other. *Disconfirming result:* the same demand
set appears regardless of the language regime (i.e. language is purely transmissive here).

### H4 — Internet as constitutive (empirical)
*Claim:* network access changes not only the quantity but the *structure* of what a group can
articulate — which sources are reachable determines which equivalences are visible.

*Design:* same task with and without network access; compare the structure of the resulting claim
networks, not just their size. *Disconfirming result:* structure is invariant to access.

### H5 — Hybridity changes accountability (interpretive)
*Claim:* the assemblage's outputs are not attributable to a single member, which changes what
accountability practices have to look like.

*Design:* trace specific outputs to their production; measure how often a single attributable author
exists, and whether existing accountability practices (review, signature, citation) survive.
*Disconfirming result:* outputs remain cleanly attributable in practice, which would make the
accountability problem rhetorical rather than structural.

## 4. Metrics

| Question | Measure | Why this one |
| --- | --- | --- |
| Accuracy | Task-specific correctness, blind-scored | The obvious outcome; not sufficient alone |
| Novelty | Proportion of ideas not present in any member's unaided output | Separates synthesis from aggregation |
| Learning / retention | Delayed post-test on the same material | Detects the deskilling risk that immediate performance hides |
| Coordination quality | Time to decision, rework rate, unresolved disagreement at deadline | Distinguishes speed from coordination |
| Deliberative diversity | Distinct framings raised before convergence | Detects homogenisation, which accuracy metrics cannot see |
| Calibration | Confidence–accuracy gap | LLM confidence is an output to evaluate, not a probability of correctness |
| Human agency | Share of decisions where a human could state the reason | The construct PCM actually cares about |
| Persistence | Re-measurement after the novelty wears off (weeks, not days) | Most "augmentation" findings are novelty effects |

Report metrics **per cell** (assemblage configuration × task type), never only as an aggregate:
aggregation can hide a configuration that helps on one task and harms on another.

## 5. Failure modes

| Failure | Mechanism | Detection |
| --- | --- | --- |
| **Hallucination** | Fluent generation without grounding | Evidence-span checks; source verification |
| **Homogenisation** | Common model style narrows the range of framings | Deliberative diversity metric (§4) |
| **Echo chambers** | Network topology reinforces existing links | Structural measures on the claim graph |
| **Deskilling** | The human stops exercising the skill the tool performs | Delayed retention test |
| **Dependency** | The assemblage cannot operate when a component is removed | Ablation: remove the LLM, measure performance |
| **Power concentration** | Access to models/infrastructure becomes the real constraint | Who can run the assemblage, and on what terms |
| **Surveillance** | Coordination metadata becomes a monitoring surface | What the system logs, and who can read it |
| **Unequal access** | Benefits accrue to those already resourced | Distribution of outcomes, not just averages |

## 6. Falsification summary

| Hypothesis | Result that would count against it |
| --- | --- |
| H1 individual extension | No gain at equal time; or gain that disappears under source-blind conditions |
| H2 collective intelligence | No group effect beyond the best individual member |
| H3 language constitutive | Identical demand sets across language regimes |
| H4 internet constitutive | Identical claim-network structure with and without access |
| H5 hybrid accountability | Outputs cleanly attributable to single members in practice |

A hypothesis that survives is evidence for the *model*, not for panpsychism. The two questions stay
separate here on purpose.

## 7. What this document does not claim

- That an LLM is conscious, or that its outputs are interpretations in the human sense.
- That a group has a mind, or that distributed processing is distributed experience.
- That extension follows from using a tool.
- That any of H1–H5 has been tested here. They are designs, not findings.

## 8. References

Extended and distributed cognition (Clark, Chalmers, Hutchins), cyborg theory (Haraway) and the
primary texts are registered in [`research/SOURCES.md`](research/SOURCES.md) §5 and §14; the
ontological and semiotic framing is in [`ONTOLOGY.md`](ONTOLOGY.md).
