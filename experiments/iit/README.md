# IIT / PyPhi experiments

These experiments study **causal integration in tiny explicit systems**. They are not consciousness tests for LLMs, humans, agent swarms, or PCM deployments.

See [`docs/IIT_AND_PYPHI.md`](../../docs/IIT_AND_PYPHI.md) for the theory and interpretation policy.

## Environment

PCM's core runtime supports Python 3.11+. Current PyPhi `main` is the in-development 2.0 / IIT 4.0 line and requires Python 3.13+, so the IIT toolchain is deliberately optional.

On Python 3.13+:

```bash
python -m pip install -e '.[iit]'
```

Then run, from the repository root:

```bash
python -m experiments.iit.recurrent_vs_feedforward
python -m experiments.iit.modular_vs_integrated
python -m experiments.iit.coupled_agents
```

The ordinary PCM test suite does not require PyPhi. PyPhi-specific tests skip when the optional dependency is absent.

## Shared assumptions

All current experiments use deterministic two-node Boolean networks. A state is `(A, B)`, with TPM rows in PyPhi's little-endian state order:

```text
(0,0), (1,0), (0,1), (1,1)
```

For every experiment:

- **boundary:** the full two-node system;
- **state:** `(1, 0)` unless otherwise stated;
- **causal model:** explicit state transition rule plus connectivity matrix;
- **quantity:** `pyphi.compute.sia(...).phi` for the full subsystem;
- **network access:** none;
- **interpretation:** system irreducibility under this toy causal model only.

Changing the state, grain, transition rule, connectivity matrix or candidate boundary may change the result. That sensitivity is scientifically relevant rather than an implementation nuisance.

## Experiment 1: recurrent vs feed-forward

File: `recurrent_vs_feedforward.py`

Models:

```text
feed-forward: A' = A, B' = A
reciprocal:   A' = B, B' = A
```

Question: how does reciprocal causal influence differ from one-way influence under the selected IIT analysis?

Limitation: these are two-bit causal systems, not abstractions validated against real neural or AI substrates.

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
