# Integrated Information Theory and PyPhi in PCM

Status: experimental research layer. IIT is one theory in PCM's consciousness portfolio, not PCM's ontology and not a consciousness detector.

## Sources and software status

Primary theory source:

- Albantakis et al. (2023), *Integrated information theory (IIT) 4.0: Formulating the properties of phenomenal existence in physical terms*, PLOS Computational Biology 19(10): e1011465. https://doi.org/10.1371/journal.pcbi.1011465

Primary software source:

- PyPhi: https://github.com/wmayner/pyphi

PCM does not depend on the old PyPI 1.x / IIT 3.0 interface. The optional `iit` extra uses the PyPhi 2.x development API on Python 3.13+ and pins an exact upstream revision in `pyproject.toml` for reproducibility:

```text
wmayner/pyphi@1f47a1e20b6a27fd92c25ec4e8a1aa5e829f8198
```

PCM itself continues to support Python 3.11+, so PyPhi remains a version-gated optional experimental dependency rather than raising the runtime floor for the project.

The current adapter uses the PyPhi 2.x API directly:

```python
substrate = pyphi.Substrate(tpm, cm=cm)
analysis = pyphi.analyze(substrate, state)
phi_s = float(analysis.phi)
```

Older code based on `pyphi.Network`, `pyphi.Subsystem`, or `pyphi.compute.sia(...)` is legacy API and should not be copied into new PCM experiments.

## 1. What IIT claims

IIT begins with proposed axioms of phenomenal existence and corresponding physical postulates. In IIT 4.0 the five phenomenal properties are:

1. **Intrinsicality**: experience exists for itself.
2. **Information**: an experience is specific, this experience rather than alternatives.
3. **Integration**: an experience is unitary and irreducible to independent experiences.
4. **Exclusion**: an experience is definite in content, boundary and grain.
5. **Composition**: experience is structured by distinctions and relations.

The corresponding physical analysis is causal rather than merely correlational. A candidate substrate must have cause-effect power upon itself from its own intrinsic perspective. IIT therefore does not identify consciousness with information volume, entropy, model size, connectivity density or computational performance.

Important IIT terms for PCM:

- **cause-effect power**: a unit or system can make a difference to, and be constrained by, possible past and future states;
- **mechanism / distinction**: a subset with irreducible causal power over a purview;
- **relations**: ways distinctions overlap and bind into a structured cause-effect organization;
- **integration / irreducibility**: how much causal power is lost under the minimum partition;
- **complex / maximal substrate**: a candidate system that is maximally irreducible relative to overlapping alternatives;
- **Phi-related quantities**: formal measures of irreducibility within IIT. Their precise definitions depend on the IIT version and level of analysis.

IIT's phenomenological axioms and its physical postulates must not be collapsed into one another. The axioms characterize properties IIT claims are essential to experience; the postulates are the theory's proposed physical realization of those properties.

## 2. IIT and PCM

PCM reserves notation as follows:

- **Psi (`Ψ`)**: PCM's optional panpsychist / Russellian-monist background or proto-conscious potential;
- **Phi (`Φ`)**: IIT and IIT-derived integration concepts only.

The symbols are not interchangeable.

A deliberately cautious PCM synthesis is:

```text
possible foundational consciousness / proto-conscious potential (Ψ)
        +
local causal integration / organization (IIT / Φ)
        +
functional access and coordination (e.g. GWT)
        +
relational coupling among agents and environment
        ->
candidate organized cognitive or conscious process
```

This is a hypothesis map, not settled doctrine.

Compatibility:

- PCM can use IIT as a theory of organization while leaving metaphysics open.
- IIT gives PCM a disciplined vocabulary for asking whether a proposed system boundary is causally integrated rather than merely connected.
- IIT's emphasis on intrinsic causal organization is useful against simplistic claims that an LLM, network or social graph is conscious because it is large or complex.

Tensions:

- PCM is open to panpsychist / Russellian-monist metaphysics; IIT 4.0 is formulated using its own methodological commitments and does not simply inherit PCM's metaphysics.
- PCM studies human-AI assemblages and distributed systems; IIT's exclusion principle makes system-boundary selection nontrivial and may favor a local complex over a larger aggregate.
- political, social and linguistic organization can be central to PCM while remaining extrinsic to an IIT substrate unless they participate in the relevant intrinsic causal structure.

A distributed system cannot be assumed conscious because its components communicate. The empirical question is whether a specified causal model becomes irreducible as a whole under IIT's formalism.

## 3. IIT and artificial systems

Applying IIT to AI requires separating several levels that are often conflated:

- **software function**: what an algorithm computes;
- **logical architecture**: recurrence, memory, attention, routing and state update rules;
- **physical substrate**: the hardware whose causal transitions instantiate the computation;
- **temporal grain**: which update interval counts as a system transition;
- **spatial/system boundary**: which units are included in the candidate system;
- **causal model**: the transition probabilities under interventions, not merely observed correlations.

Under IIT, functional equivalence does not guarantee identical consciousness. A stored-program machine can simulate a causal organization without necessarily possessing the same intrinsic cause-effect structure.

For current LLMs, the following are explicitly **not** proxies for Phi:

- parameter count;
- attention weights;
- embedding dimensionality;
- token entropy or perplexity;
- benchmark score;
- number of agents in a swarm;
- graph density;
- amount of memory.

Direct PyPhi computation on a full transformer, production multi-agent swarm, large neural network or social graph is out of scope. Both the combinatorics and the causal-model assumptions make such a calculation computationally and conceptually inappropriate.

## 4. Why toy models are useful

Toy causal networks let PCM ask narrow questions without pretending to measure modern AI consciousness:

- Does adding reciprocal causal coupling make a model less decomposable?
- Does a recurrent loop differ from a feed-forward chain under a selected IIT formalism?
- When do two coupled subsystems form one candidate complex rather than two?
- Which result changes when the system boundary changes?
- How sensitive is integration to coupling direction, probabilistic assumptions, and formalism choice?

The experiments in `experiments/iit/` therefore use tiny Boolean systems with explicit transition probability matrices (TPMs).

Each experiment should record:

1. PyPhi revision and selected formalism;
2. units and state;
3. deterministic or probabilistic update rule / TPM;
4. connectivity assumptions;
5. system boundary;
6. PyPhi quantity computed;
7. interpretation;
8. limitations.

### Deterministic-network caveat

The pinned PyPhi development line defaults to the current IIT 4.0 formalism, under which deterministic networks can return `φ_s = 0`. This matters for PCM because the current fixtures are intentionally deterministic.

A zero value is not automatically a failed experiment, and it must not be promoted into a claim that the corresponding real system is unconscious. These toy systems remain useful for testing causal-model construction, boundary assumptions, API compatibility, and sensitivity to formalism. If a future comparison depends on a non-zero published IIT result, the experiment must explicitly select and document the matching formalism rather than silently relying on defaults.

## 5. PyPhi integration policy

PCM keeps PyPhi outside the core runtime.

The optional `iit` dependency targets the pinned PyPhi 2.x development revision only on Python 3.13+, because that is the API used by the IIT 4.0 experiment layer. PCM's normal Python 3.11+ environment and CI remain valid without it.

Install the reproducible IIT environment with:

```bash
python -m pip install -e '.[dev,iit]'
```

Run the IIT test slice with:

```bash
python -m pytest -q -m iit
```

The experiment modules still import without PyPhi installed. Functions that perform PyPhi calculations import it lazily and raise a clear optional-dependency error, while PyPhi-specific tests skip cleanly when the dependency is absent.

PyPhi is computationally expensive by design because partitions, purviews and candidate systems proliferate combinatorially. Keep experiments tiny.

## 6. Experiments

### A. Recurrent vs feed-forward

`experiments/iit/recurrent_vs_feedforward.py`

Compare two deterministic two-bit causal systems:

- feed-forward: `A' = A`, `B' = A`;
- reciprocal: `A' = B`, `B' = A`.

The comparison asks how bidirectional causal dependence differs from a one-way organization under a specified IIT analysis. Under the current default formalism, deterministic systems may both produce zero system integrated information, so interpretation must include the selected formalism and causal structure rather than assuming that recurrence should automatically produce a larger scalar.

### B. Modular vs integrated

`experiments/iit/toy_networks.py`

Construct reusable tiny TPMs for independent, feed-forward, reciprocal and cross-coupled units. These definitions are deterministic and testable without PyPhi.

### C. Coupled agents

`experiments/iit/coupled_agents.py`

Represent two toy agents by one binary state each and compare:

- independent persistence;
- one-way coupling;
- reciprocal coupling.

This is a causal toy model of relational organization. It is not a model of a human, an LLM or phenomenology.

## 7. Relation to Pancyberpsychism

The comparison in `docs/PANCYBERPSYCHISM.md` separates three layers:

```text
Ψ                 foundational / metaphysical background
Φ                 IIT-style local or system irreducibility
relational layer  coupling, mutual influence, persistence and adaptation
```

The interesting experiment is whether changing relational coupling changes the IIT structure of a *combined explicitly modeled system*.

This does not validate Pancyberpsychism's equations or imply that relational synchrony equals consciousness. PCM does not reuse `psi_rel` or `Psi_total`; descriptive names such as `reciprocal_coupling` and `cross_system_influence` are preferred.

## 8. Interpretation rules

A positive or larger Phi-like result in these experiments means, at most:

> Under this particular IIT formalism, PyPhi revision, causal model, grain, state and system boundary, the modeled system is more irreducible by the selected measure.

It does **not** establish:

- subjective experience;
- personhood;
- moral status;
- consciousness in an LLM;
- consciousness in a real human-machine dyad;
- consciousness in PCM as a whole.

Conversely, a zero or low result for a toy abstraction does not establish that the real system it loosely represents is unconscious.

## 9. PCM research questions

The initial IIT track should stay narrow:

1. reproduce small canonical PyPhi calculations with explicit version/formalism metadata;
2. compare feed-forward and recurrent causal organization;
3. vary reciprocal coupling in tiny agent models;
4. test sensitivity to boundary, grain, probabilistic dynamics, and formalism;
5. record disagreements between IIT predictions and functional / relational theories rather than averaging theories into one score.

The design principle is simple:

> **Use PyPhi to study integration in explicit toy causal systems, not as a magical consciousness detector for modern AI.**
