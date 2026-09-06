# PCM User Guide

> **PCM is a local-first social operating system for human–AI Rhizomes.**
> This guide teaches the practical workflows. Philosophy lives in
> [PANPSYCHIC_CYBORG_MULTITUDE.md](PANPSYCHIC_CYBORG_MULTITUDE.md) — it is
> not repeated here.

**Basic vocabulary:**

- **Member** — a node of the rhizome: a biological human or a
  technological node (an AI agent).
- **Assemblage** — a composite actor: human + LLM + language + tools +
  memory + network, modeled as one member with identifiable components.
- **Rhizome** — a local, self-governing collective of members
  (Deleuze & Guattari: no root, no center, no fixed hierarchy).
- **Common** — the memory, knowledge, code, resources and relationships
  produced and governed together.
- **Multitude** — the wider network of rhizomes.

Every command below has been executed against the real CLI. Nothing is
invented. For full options always run:

```bash
python multitude.py COMMAND --help
```

---

## 1. Installation

```bash
git clone https://github.com/TomiToivio/Panpsychic_Cyborg_Multitude.git
cd Panpsychic_Cyborg_Multitude

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Python 3.12+ is what the repository is developed against. The **core
kernel requires only the standard library plus Pydantic** — Ollama,
zenoh, Telegram, BCI and embodiment support are all *optional at
runtime*: PCM works without any of them (see §6, §9, §10, §11).

---

## 2. Your first Rhizome

```bash
python multitude.py found --name "My Rhizome" --founder alice
```

Output tells you where the rhizome lives on disk:

```text
founded: My Rhizome
rhizome dir: data/tribes/my-rhizome
founder: alice (biological, voting)
```

`found` created two things: `data/tribes/my-rhizome/tribe.json`
(discovery metadata) and `data/tribes/my-rhizome/events.jsonl` (the
append-only event log — the authoritative state, §12).

Check the state and add members:

```bash
python multitude.py status
python multitude.py members
python multitude.py join --as bob --kind biological
python multitude.py say --as alice --text "Hello Rhizome."
```

**Which rhizome am I operating on?** By default PCM picks the most
recently used rhizome under the data root. To target one explicitly:

```bash
python multitude.py status --rhizome data/tribes/my-rhizome
```

(`--tribe` still works as a legacy alias; `--rhizome` is primary.)

---

## 3. Shared and private memory

**Shared memory** is visible to every member of the rhizome:

```bash
python multitude.py remember --as alice --title "Guide memory" --text "PCM works."
python multitude.py search --query "works"
```

**Private notes** are per-member, stored locally
(`private_notes.jsonl`), and never appear in shared memory:

```bash
python multitude.py private-note-add --as bob --title "Private" --text "my private thought"
python multitude.py private-notes --as bob
```

> **Private memory stays local until explicitly published.**

Publishing is an explicit, member-owned act:

```bash
python multitude.py private-note-publish --as bob \
    --note pnote-2026... --by bob
```

The published copy enters shared memory as a new memory entry with a
link back to its source note.

---

## 4. Governance: one complete proposal lifecycle

```bash
# 1. open a proposal (rule: consensus | majority | unanimity ...)
python multitude.py propose --by alice --title "Adopt weekly sync" \
    --text "We meet every Monday."

# 2. list open proposals
python multitude.py proposals --open

# 3. vote (positions: for | against | abstain | block)
python multitude.py vote --proposal prop-2026... --as bob --position for

# 4. close and record the decision
python multitude.py close --proposal prop-2026... --by alice
```

Closing records a decision event (`decision dec-...`) with the tally.
Notes:

- **Consensus** (default) counts `for`/`against`/`abstain` and honors
  **block** — a block vote prevents adoption.
- **Majority** and **unanimity** are alternative rules selectable at
  proposal time (`propose --rule`).
- **Quorum** is derived from the voting membership; the vote output
  shows `cast N, quorum M`.

Governance rules themselves can be recorded:

```bash
python multitude.py rule-define --by alice --title "Be kind" \
    --description "kindness rule"
python multitude.py rules
```

---

## 5. Human and AI members

```bash
python multitude.py join --as bob --kind biological
python multitude.py join --as "PCM node" --kind technological \
    --model "gemma4:e4b" --persona "helpful rhizome steward"
```

Technological nodes speak through **Ollama** (local, no cloud):

- `PCM_OLLAMA_HOST` — Ollama address (default `http://localhost:11434`)
- `PCM_OLLAMA_MODEL` — model name (default `gemma4:e4b`)
- `PCM_OLLAMA_TIMEOUT` — request timeout seconds (default 180)

Ask a technological node to speak:

```bash
python multitude.py counsel --as "PCM node" --topic "how should we split work?"
```

> **PCM works without an LLM.** Every feature in this guide functions
> with only biological members; AI agents are optional participants.

The Hermes integration (`src/multitude/integrations/hermes/`) is a thin
adapter for running Hermes agents as members — usable, but it is an
integration layer, not a requirement.

---

## 6. Goals, tasks and the Common

The economy/care surface — a few common workflows:

```bash
python multitude.py goal-open --by alice --title "Ship guide" \
    --text "finish user guide" --category social
python multitude.py task-open --by alice --title "Write docs"
python multitude.py task-claim --task task-2026... --as bob
python multitude.py task-done --task task-2026... --as bob

python multitude.py work-log --as alice --description "wrote guide" --hours 2
python multitude.py work-summary

python multitude.py resource-register --by alice --name "meeting room"
python multitude.py resource-allocate --resource res-2026... --to bob --purpose "workshop"
```

Commitments, agreements, care and rhythms:

```bash
python multitude.py commitment-record --by bob --title "review docs" \
    --owed-by bob --owed-to alice
python multitude.py agreement-record --by alice --title "doc pact" \
    --party alice --party bob
python multitude.py care-record --by alice --member bob \
    --summary "morning check-in" --type check_in
python multitude.py rhythm-define --by alice --name "weekly sync" \
    --cadence weekly --purpose "stay in sync"
```

A shared lexicon keeps terminology explicit:

```bash
python multitude.py lexicon-add --term "Rhizome" \
    --definition "local self-governing collective"
python multitude.py lexicon
```

Do not memorize every flag — `--help` is complete:

```bash
python multitude.py COMMAND --help
```

---

## 7. ValueFlows (optional economic domain)

> **PCM governs the Rhizome; ValueFlows describes what flows through
> the Common.**

ValueFlows (`src/multitude/economy_vf.py`, full mapping in
[VALUEFLOWS.md](VALUEFLOWS.md)) is an optional semantic layer. Core
entities: **Agent, Intent, Commitment, EconomicEvent, EconomicResource,
Process, Agreement**.

```bash
python multitude.py intent-record --by alice --title "need: help testing" --kind need
python multitude.py intents
```

What ValueFlows in PCM does **not** do:

- no cryptocurrency, no tokens;
- no automatic monetization of contributions;
- care, research, documentation and knowledge are first-class
  contribution kinds.

ValueFlows records *what flows*; governance decides *what should
happen*.

---

## 8. Networking

Three modes:

**Local-only (default).** Everything lives under `data/`; no network
activity. This is the simplest and private-by-default mode.

**Zenoh (optional node fabric).** For rhizome-to-rhizome and
device-to-rhizome exchange:

```bash
export PCM_ZENOH_ENABLED=true
python3 -m unittest tests.test_pcm_phase2_zenoh   # two-node demo
```

Architecture and security model: [NETWORKING_STACK.md](NETWORKING_STACK.md).

**Other interfaces.** `python multitude.py serve-api` runs a minimal
local JSON API; `python multitude.py telegram` runs the Telegram
gateway (requires a repo `.env` with the bot token). The Hermes
integration runs agents as members. These adapters are thin and real —
but they are transports, not core features.

---

## 9. Optional BCI (experimental)

The BCI integration (`src/multitude/integrations/bci.py`, research in
[docs/research/PCM_BCI_CYBORG_INTEGRATION.md](docs/research/PCM_BCI_CYBORG_INTEGRATION.md))
is an **experimental, optional** adapter between a biological member
and the assemblage. The rules it enforces:

- **derived context only** — `BCIObservation` (signal, value,
  confidence, layer), never raw EEG;
- raw biosignals stay local;
- observations are **private by default** — nothing is recorded or
  shared until the human member explicitly publishes that observation;
- **consent is human-controlled** — AI agents cannot enable monitoring
  or change consent settings (kernel-enforced, tested);
- **no consciousness measurement** — EEG-derived estimates are
  psychic-layer *context*, never a detector of experience.

There is no CLI for BCI: it is a Python integration point
(`BCIAdapter` / `BCIHub`) intended for adapters of real devices later.
The current reference implementation is synthetic (test-oriented).

---

## 10. Optional embodiment (first step)

The embodiment module (`src/multitude/integrations/embodiment.py`) is
the minimal device architecture — **a foundation, not a Home Assistant
or robot platform**:

```text
structured action → capability → policy → PhysicalDevice → verified state
```

`SimulatedLight` is the reference device (on/off + `power.set`), so the
whole pipeline is testable without hardware. The module is **disabled
by default**: enable with `PCM_EMBODIMENT_ENABLED=true`. Real
integrations (Home Assistant, MQTT, drones, ROS 2) remain roadmap
items — each is one new `PhysicalDevice` implementation away, none is
implemented yet.

Safety chain, even in simulation: structured commands only; capability
allowlist; fail-closed policy (default DENY); resulting state verified
by read-back; every action journaled with provenance.

---

## 11. Data and backup

Where things live (all overridable with `PCM_DATA_DIR`):

```text
$PCM_DATA_DIR (default: <repo>/data/)
└── tribes/
    └── <rhizome-slug>/
        ├── events.jsonl          ← THE authoritative state (append-only log)
        ├── tribe.json            ← discovery metadata (name, charter, slug)
        └── private_notes.jsonl  ← per-member private notes (stays local)
```

- The **event log is the state**: every fact PCM knows is an appended,
  provenance-stamped event. Deleting or editing the log corrupts
  history — back it up, don't rewrite it.
- **Backup = copy the rhizome directory** (`events.jsonl` +
  `tribe.json`). Replay rebuilds all state from the log alone.
- Private notes are a separate file per rhizome — include them in
  backups only if you are their owner.

**Legacy naming, intentional:** the current term is *Rhizome*, but
persisted paths and files still use the older wire names —
`data/tribes/`, `tribe.json`, `tribe_role`. These are **disk/wire
compatibility names, not conceptual terminology**, and renaming them is
not safe for existing rhizomes. PCM's own CLI help and errors already
say *rhizome*.

---

## 12. Security and privacy

Practical rules, no stronger than the implementation:

- **Local-first** — all state lives under your data directory; nothing
  phones home.
- **Private memory stays private** — private notes are a separate local
  file; publication is an explicit per-note act.
- **Authenticated ≠ authorized** — a valid signature proves who sent
  an envelope; the fail-closed policy decides whether the action is
  allowed (default DENY).
- **Biosignal privacy** — raw signals never leave the device; derived
  context is private until a human publishes it; AI agents cannot
  change consent settings.
- **Embodiment is fail-closed** — capability allowlist + policy check +
  verified read-back, disabled by default.
- **Known limitation** — confidentiality of fabric traffic (Phase 3b)
  is still gated work; do not send secrets over zenoh today.

---

## 13. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `no rhizomes found under ...` | No rhizome exists yet — run `found` first, or pass the right directory with `--rhizome DIR`. |
| Wrong rhizome selected | PCM picks the most recently used rhizome; target explicitly with `--rhizome DIR`. |
| `counsel` fails / model unavailable | Ollama not running or model missing: check `PCM_OLLAMA_HOST`, run `ollama pull <model>`. PCM works without it. |
| Zenoh unavailable | Fabric is opt-in: `PCM_ZENOH_ENABLED=true` and a zenohd-compatible runtime are required; otherwise everything stays local. |
| `embodiment is disabled` | Set `PCM_EMBODIMENT_ENABLED=true` — it is off by default. |
| Where do I inspect history? | `python multitude.py log` prints the raw event log; the file is `<rhizome-dir>/events.jsonl`. |
| A technological node won't vote | Check `members`: voting can be revoked (`demote`) or omitted at join (`--no-vote`); `promote` restores it. |

---

## 14. Command discovery

```bash
python multitude.py --help
python multitude.py COMMAND --help
```

The CLI is the complete surface: found/join/say, memory, governance,
layers, devices, economy, ValueFlows, care, rhythms, terms, agents,
goals/tasks, and the optional gateways. This guide taught the
workflows; `--help` knows every flag.