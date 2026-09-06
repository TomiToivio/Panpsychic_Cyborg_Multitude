# ValueFlows in PCM — economic coordination and the production of the Common

> **"The Common is not what exists before cooperation; it is continuously
> produced and reproduced through cooperation. ValueFlows gives PCM a
> vocabulary for recording those flows without reducing them to money,
> private property, or corporate accounting."**

**Version:** 1.0 (2026-09-06, issue #11)
**Module:** `src/multitude/economy_vf.py` (domain layer over the event-sourced kernel)
**Standard:** [ValueFlows](https://valueflows.app) — vocabulary for distributed economic networks
**Ontology namespace:** `https://w3id.org/valueflows/ont/vf#`

---

## Why ValueFlows fits PCM

ValueFlows is designed for economic coordination **inside and between
independent agents and organizations** — it does not assume money, a
single enterprise, or any global economic authority. That is exactly
PCM's situation: rhizomes of humans, AI assemblages, devices and partner
rhizomes producing the Common together.

ValueFlows should be described as helping PCM make **the Common**
technically legible. In PCM the Common includes shared knowledge,
language, code, social relationships, care, productive capacities,
common resources, institutions, infrastructures, and collectively
produced value. None of those are commodities; none of them should have
to pass through a ledger of money to count.

---

## The Hardt & Negri framing

### Multitude

The Multitude consists of heterogeneous singularities that remain
different while acting together. Therefore:

> **ValueFlows must not turn the Rhizome into one corporate economic actor.**

Humans, AI assemblages, organizations, other rhizomes, and eventually
ecological agents remain **individually identifiable participants** in
every flow. The `vf_agent_ref` projection carries each participant's PCM
provenance kind (`member` / `assemblage` / `economic_agent`) and, for
assemblages, the component list — composition never erases the parts.

### Cooperation

Cooperation is productive in itself. PCM records the whole chain:

```text
need
  ↓
intent            vf_intent_created
  ↓
coordination
  ↓
commitment        vf_commitment_created     (what was PROMISED)
  ↓
work / contribution
  ↓
economic event    vf_economic_event_recorded (what HAPPENED)
  ↓
resource / capability / knowledge
                  vf_resource_created
  ↓
the Common
```

### Biopolitical / immaterial production

"economic value" is **not** restricted to commodities or money. The
action vocabulary and record kinds describe contributions such as
programming, research, moderation, teaching, documentation, emotional /
care work, maintenance, datasets, shared memory, knowledge, creative
work, and physical resources. **No monetary value is assigned
automatically** — recognition and distribution stay with PCM governance
(`RhizomeEconomyProfileRecord`, distribution logic, solidarity policy),
never with the flow vocabulary.

### Autonomy

The separation is constitutional:

> **ValueFlows describes *what flows*. PCM governance determines *what
> should happen and under which rules*.**

The `economy_vf` domain records; it never decides. Proposals, votes and
the charter remain the only paths through which coordination rules
change.

---

## Concept mapping

```text
PCM                              ValueFlows

Member / Assemblage          ↔   Agent
need / offer / goal          ↔   Intent
proposal for exchange        ↔   Proposal
agreement                    ↔   Agreement
promise to contribute        ↔   Commitment
actual contribution          ↔   EconomicEvent
shared resource              ↔   EconomicResource
collective activity          ↔   Process
```

Only genuinely corresponding concepts are mapped — PCM objects without a
VF counterpart (charter, layers, biosignals) are not forced in.

### Commitment vs EconomicEvent — the constitutional distinction

> **A Commitment represents what was promised. An EconomicEvent
> represents what actually happened.**

ValueFlows explicitly distinguishes planning concepts (Intent,
Commitment) from observed EconomicEvents. PCM preserves the distinction
in separate stores (`vf_store["commitments"]` vs
`vf_store["economic_events"]`) and separate event types — a commitment
may live for years without an event, an event may occur with no
commitment behind it, and neither implies the other.

### Assemblages as economic agents

```text
human
 + LLM
 + tools
 + memory
 + Internet
       ↓
PCM Assemblage        (AssemblageRecord — components stay identifiable)
       ↓
ValueFlows Agent      (vf:Organization with per-component provenance)
```

The assemblage may act economically as **one agent** while PCM retains
provenance about which humans, AIs, tools or devices participated —
that retention is what makes accountability possible.

### Rhizome-to-rhizome cooperation

```text
Rhizome A  ↓ offers research
Rhizome B  ↓ offers compute
Agreement → Commitments → EconomicEvents → shared output → the Common
```

No global economic authority is required: agents reference each other
by provenance-carrying URIs (`urn:pcm:...`), and the JSON-LD projection
is what crosses rhizome boundaries later.

---

## Implementation

- **Records** (`multitude.models`): `EconomicEventVFRecord`,
  `EconomicResourceVFRecord`, `ProcessVFRecord` (join the existing
  `EconomicIntentRecord` / `EconomicCommitmentRecord` /
  `EconomicAgreementRecord`).
- **Domain** (`multitude.economy_vf`): event vocabulary `vf_*`
  (six types), domain reducer registered through
  `multitude.domains.register_domain("valueflows", ...)` — the core
  kernel never branches on VF types.
- **Kernel methods** (`Rhizome`): `vf_create_intent`,
  `vf_create_agreement`, `vf_create_commitment`,
  `vf_record_economic_event`, `vf_create_resource`, `vf_create_process`
  — validate references, then emit append-only events.
- **Interoperability:** `to_jsonld(rhizome, kind, id)` projects any
  stored record to JSON-LD in the VF namespace. PCM does **not** require
  RDF internally — the projection is at the boundary, and `pcm:*`
  properties carry internal IDs and metadata so nothing is lost in
  round-trips.

### Privacy and scope

ValueFlows records flows, not surveillance: no automatic monetary
valuation, no export of private notes or consent-gated biosignals, and
no BCI-derived data in economic events (the BCI adapter publishes only
what a human explicitly publishes). Care, maintenance and knowledge
flows are first-class citizens — the point is recognizing the
production of the Common, not metering it.

---

*The Common is produced. ValueFlows records the production. Governance
stays with the rhizome.*