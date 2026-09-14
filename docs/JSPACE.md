# J-Space integration

PCM treats `keuranos/jspace-lab` as optional research instrumentation for technological members. It is not a core dependency and does not make Qwen, CUDA, PyTorch, bitsandbytes, or a Jacobian lens part of the PCM runtime.

Upstream: https://github.com/keuranos/jspace-lab

Related work:

- #38 covers the broader Aion/J-Space calibration architecture.
- #39 covers the reusable self-knowledge benchmark.
- #40 covers the live J-Space instrument and transport bridge implemented here.

## What the upstream tool exposes

The upstream lab combines a model server with a fitted Jacobian lens and exposes emitted tokens, a selected mid/deep-layer readout, per-layer candidate trajectories, provider-specific metrics, disagreement/veto flags, ASK mode, SSE streaming, a browser UI, and JSONL traces.

The UI is a visualization client, not the measurement protocol. PCM therefore integrates at the transport/observation boundary rather than copying the upstream HTML.

PCM's interpretation rule is strict:

```text
layer readout != thought != belief != self != consciousness
```

These values are measurements from a particular instrument and calibration procedure.

## PCM provider

`src/multitude/integrations/introspection/__init__.py` defines:

- `LiveIntrospectionProvider`, a generic provider protocol;
- `IntrospectionFrame` and `IntrospectionObservation`, normalized read-only structures;
- `RetentionMode` with `none`, `summary`, and `full` modes;
- `JSpaceLabProvider`, the jspace-lab adapter;
- `parse_sse_blocks()`, a chunk-safe SSE parser.

The adapter uses only the Python standard library. It does not import upstream jspace-lab code or any model/GPU library.

Provider-native values such as `engagement_score`, `concept_mass`, or veto flags stay inside provider-specific metadata/flags. They are not promoted into the PCM ontology and are never treated as consciousness scores.

## ASK mode and streaming

The upstream ASK endpoint streams SSE events including `ask_token`, `ask_done`, and `error`. PCM buffers across arbitrary HTTP chunks and parses JSON carried in `data:` records.

The endpoint is configurable. No Aion path or localhost port is hard-coded. Prompt provenance is represented with a SHA-256 digest instead of automatically persisting raw prompt text.

`stream_events()` can normalize an already-open SSE stream for dashboards and tests. The baseline adapter performs no automatic retry, avoiding duplicate expensive generations.

## Retention and privacy

Three retention modes are available:

- `none`: do not retain normalized frames;
- `summary` (default): retain selected token/layer, provider metrics and flags while dropping the raw event and full layer ladder;
- `full`: retain raw provider events and layer candidates for explicit research runs.

Full traces may reveal prompts, system context, model internals, or other sensitive information. Full retention must therefore be explicit and should not be broadcast across a Rhizome by default.

## Relationship to agent-introspection-bench

Issue #39's benchmark still works without J-Space. J-Space can optionally supply its internal-readout channel:

```text
(a) emitted answer
(b) jspace-lab instrument observation
(c) optional causal intervention
(d) live PCM/runtime ground truth
```

This supports experiments on self-model calibration and agent epistemology without making hidden-state probes mandatory.

## Authority boundary

The integration is read-only. Receiving an observation does not authorize memory writes, identity changes, voting, governance actions, tool use, or model intervention. Any later use of a measurement must go through PCM's normal permission and provenance paths.

Causal ablation/de-veto work remains separate experimental tooling.

## Visualization

Prefer linking to or reusing the upstream jspace-lab UI rather than forking it into PCM. Any future PCM dashboard should visibly label values as instrument readouts and must not present them as what an AI `really thinks`.

## Tests

`tests/test_jspace_lab_integration.py` uses fake SSE data only. It covers chunk-boundary parsing, normalization, partial frames, retention modes, namespaced metrics, and the absence of governance/memory mutation surfaces. No network, GPU, Ollama, model, or running jspace-lab process is required.
