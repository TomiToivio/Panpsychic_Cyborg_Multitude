# IIT / PyPhi experiments

These experiments study **causal integration in tiny explicit systems**. They are not consciousness tests for LLMs, humans, agent swarms, or PCM deployments.

See [`docs/IIT_AND_PYPHI.md`](../../docs/IIT_AND_PYPHI.md) for the theory and interpretation policy.

## Environment

PCM's core runtime supports Python 3.11+. The optional IIT toolchain targets the PyPhi 2.x development API on Python 3.13+ and is pinned in `pyproject.toml` to a specific upstream commit for reproducibility:

```text
wmayner/pyphi@1f47a1e20b6a27fd92c25ec4e8a1aa5e829f8198
```

On Python 3.13+:

```bash
python -m pip install -e '.[dev,iit]'
```

Run the IIT tests with:

```bash
python -m pytest -q -m iit
```

Then run the experiments, from the repository root:

```bash
python -m experiments.iit.recurrent_vs_feedforward
python -m experiments.iit.modular_vs_integrated
python -m experiments.iit.coupled_agents
```

The ordinary PCM runtime does not require PyPhi. PyPhi-specific tests skip when the optional dependency is absent.

## Current PyPhi API used by PCM

PCM uses the current pinned PyPhi 2.x interface:

```python
substrate = pyphi.Substrate(tpm, cm=cm)
analysis = pyphi.analyze(substrate, state)
phi_s = float(analysis.phi)
```

Older examples based on `pyphi.Network`, `pyphi.Subsystem`, or `pyphi.compute.sia(...)` do not describe the API used by this repository. The compatibility layer lives in `experiments/iit/toy_networks.py` and keeps all PyPhi imports lazy so the core package remains independent of PyPhi.

## Shared assumptions

All current experiments use deterministic two-node Boolean networks. A state is `(A, B)`, with TPM rows in PyPhi's little-endian state order:

```text
(0,0), (1,0), (0,1), (1,1)
```

For every experiment:

- **boundary:** the full two-node system;
- **state:** `(1, 0)` unless otherwise stated;
- **causal model:** explicit state transition rule plus connectivity matrix;
- **quantity:** system integrated information `analysis.phi` (`φ_s`) returned by `pyphi.analyze(...)`;
- **network access:** none;
- **interpretation:** system irreducibility under this toy causal model only.

Changing the state, grain, transition rule, connectivity matrix, candidate boundary, or selected IIT formalism may change the result. That sensitivity is scientifically relevant rather than an implementation nuisance.

### Deterministic-network caveat

The pinned PyPhi development line defaults to the current IIT 4.0 formalism, under which deterministic toy networks can yield `φ_s = 0`. A zero value is therefore not automatically a failed experiment and must not be interpreted as a general claim about consciousness. These fixtures are useful for testing explicit causal models, API integration, boundary assumptions, and formalism sensitivity. If a future experiment switches to another formalism or introduces probabilistic dynamics, it must record that choice explicitly.

## Experiment 1: recurrent vs feed-forward

File: `recurrent_vs_feedforward.py`

Models:

```text
feed-forward: A' = A, B' = A
reciprocal:   A' = B, B' = A
```

Question: how does reciprocal causal influence differ from one-way influence under the selected IIT analysis?

Limitation: these are two-bit causal systems, not abstractions validated against real neural or AI substrates. Under the default current formalism, both may have zero system integrated information; the scientifically relevant comparison includes the causal structure and formalism assumptions, not only a hoped-for non-zero scalar.

## Experiment 2: modular vs integrated

File: `modular_vs_integrated.py`

Models:

```text
modular:    A' = A,        B' = B
recurrent:  A' = A OR B,   B' = A OR B
```

Question: how does a disconnected pair compare with a jointly recurrent model?

Limitation: coupling density alone is not IIT. The actual TPM and intrinsic cause-effect structure determine the analysis.

## Experiment 3: coupled toy agents

File: `coupled_agents.py`

Treat A and B only as labels for two toy agent states and compare:

1. independent persistence;
2. one-way influence;
3. reciprocal influence.

Question: can changing cross-agent causal assumptions alter integration of the combined model?

This experiment is coordinated conceptually with [`docs/PANCYBERPSYCHISM.md`](../../docs/PANCYBERPSYCHISM.md). Even if reciprocal coupling produces a different IIT result, it does not follow that a real relationship has become a conscious subject.

## Reproducibility rule

If an experiment grows beyond a few binary units, document why the larger causal model is necessary before adding it. PyPhi computations scale combinatorially, and a larger model can create an impressive runtime without creating a better scientific question.

Record at least the PyPhi revision, IIT formalism, system state, TPM, connectivity matrix, candidate boundary, and reported quantity for any result intended for comparison or publication.
