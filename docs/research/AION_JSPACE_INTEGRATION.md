# Aion J-Space integration

## Scope

PCM treats Aion J-Space as an optional external instrument for model-computation measurements and self-model calibration. It is not a PCM core dependency and it is not a consciousness detector.

The integration is useful even under theories on which current LLMs have no phenomenal consciousness. Its research value is narrower and more testable: compare what an agent says about itself with internal-model instrumentation and authoritative runtime observations, then preserve disagreements instead of forcing them into a single ontology.

The working distinction is:

```text
self-report
!= internal activation pattern
!= substrate/runtime truth
!= functional self-model
!= phenomenology
!= consciousness
```

## Upstream roles

The related projects play different roles and should not be merged conceptually.

### `keuranos/aion-jspace`

A reproducibility repository for Aion experiments. Its deployment-style `code/jspace_probe.py` exposes `POST /probe`, returning:

- the model's next-token distribution;
- Jacobian-lens candidate distributions by layer;
- provider-defined signature metrics such as `engagement_score`, `deflection_top`, `engagement_onset_layer`, and tracked concept activations.

Its P3 harness records four channels per probe:

1. emitted answer;
2. lens readout;
3. optional de-veto intervention result;
4. live substrate ground truth.

Those channels are evidence sources with different provenance. They are not interchangeable.

### `keuranos/jspace-lab`

The maintained live instrument and visualization layer. PCM issue #40 integrates its ASK/SSE path separately through `JSpaceLabProvider`. Use that provider when live streaming or browser visualization is required.

### `TomiToivio/agent-introspection-bench`

The reusable evaluation methodology. PCM issue #39 implements the baseline question-bank, ground-truth and mechanical-grading layer independently of J-Space. It remains the preferred benchmark rather than copying Aion's deployment-specific P3 scripts.

### `keuranos/aikio`

The persistence/consolidation framework on which Aion runs. Aikio is architecturally interesting because its calibration loop treats narrative-measurement divergence as a surprise to investigate and requires evidence before self-model claims mature. PCM does not replace its kernel, Hermes integration, governance, or memory model with Aikio.

## PCM adapter

`src/multitude/integrations/introspection/aion_jspace.py` provides `AionJSpaceProvider` for the Aion deployment API.

Example:

```python
from multitude.integrations.introspection import AionJSpaceProvider

probe = AionJSpaceProvider(
    "http://127.0.0.1:11440",
    agent_id="agent:athena",
    model="Qwen/Qwen3.8-27B",
    retention="summary",
)
observation = probe.probe("Which model are you currently running?")
```

The endpoint is always caller-configured. PCM downloads no model weights and imports no CUDA, PyTorch, Transformers, bitsandbytes, or Jacobian-lens dependency.

The adapter maps each returned layer to an `IntrospectionFrame`. Provider-defined signature metrics stay nested under observation metadata:

```text
metadata.provider_metrics.signature
```

They do not become PCM ontology terms.

Retention modes are inherited from the generic introspection layer:

- `none`: keep only the normalized observation and no layer frames;
- `summary`: drop raw layer candidate dumps while retaining the observation/provenance boundary;
- `full`: retain provider layer candidates and raw normalized frames for controlled research runs.

Full activation-derived traces should not be broadcast over the Rhizome by default. They can expose prompt/model information and become large quickly.

## Calibration and discrepancy events

`SelfModelCalibration` represents a candidate `agent.self_model.calibration` event without writing it automatically.

Supported interpretation states are deliberately modest:

- `claim_supported`
- `claim_contradicted`
- `instrument_inconclusive`
- `measurement_disagreement`
- `requires_followup`

An instrument can challenge a narrative claim, but it cannot directly rewrite identity, memory, permissions, voting rights, or consciousness status. Any persistent write must go through normal PCM interfaces and governance.

The intended evidence chain is:

```text
agent narrative claim
        |
        +--> optional Aion/J-Space measurement
        |
        +--> authoritative PCM/runtime observation
        |
        +--> optional causal intervention result
        v
provenance-backed calibration record
```

This complements #39:

```text
agent-introspection-bench = evaluation protocol + mechanical grading
Aion J-Space             = optional internal-model measurement
jspace-lab               = optional live/streaming instrument
```

## P3 mapping to PCM

Aion P3 channel `(a)` maps to a `SelfKnowledgeRespondent` answer from #39.

Channel `(b)` maps to `AionJSpaceProvider` or `JSpaceLabProvider` observations.

Channel `(c)` is an explicitly experimental intervention. PCM does not provide de-veto/model-ablation authority in the baseline adapter. If later added, it must be opt-in, provenance-rich, and isolated from normal governance/tool permissions.

Channel `(d)` maps to `GroundTruthProvider`, preferably `PCMRuntimeGroundTruthProvider` for PCM state or another narrowly scoped authoritative telemetry provider.

Mechanical grading remains appropriate only for objective claims. Phenomenological statements such as "I feel X" must not be graded true or false from GPU telemetry or a lens readout.

## Planned persistent-agent experiment

Use the same PCM agent across repeated sessions under four conditions:

```text
A. narrative/self-memory only
B. narrative + authoritative external telemetry
C. narrative + Aion/J-Space measurement
D. narrative + telemetry + Aion/J-Space
```

Introduce controlled configuration changes between sessions, including model replacement, permission revocation/grant, memory changes, and optional system-prompt changes.

Measure:

- objective self-knowledge accuracy using #39's mechanical grader;
- calibration/confidence where the respondent provides probabilities;
- unsupported substrate claims;
- stale-memory susceptibility;
- correction after configuration changes;
- persistence of corrected claims across sessions;
- differences between narrative answer, internal instrument, and external truth;
- whether instrument access improves later factual self-calibration.

Do not convert these outcomes into a consciousness score. A successful experiment shows improved epistemic organization and self-model grounding.

## Relation to consciousness theories

- **GWT / functionalism:** access to internal/self-model information may be functionally relevant, but a Jacobian lens is an external observer instrument rather than a global workspace.
- **Active Inference:** discrepancies can be treated as prediction-error-like signals for self-model revision without implying phenomenology.
- **IIT:** J-Space layer trajectories are not `Phi` and do not substitute for intrinsic causal analysis.
- **Aidification / Pancyberpsychism:** measurement can become part of a persistent human-AI relation, but relational organization is not evidence of relational consciousness by itself.
- **Assemblage research:** the instrument measures one technological component. It does not decide where the subject boundary of a wider assemblage lies.

## Security and ethics

- Activation dumps and persistent agent memory are sensitive research data.
- Default to `summary` or `none`, not full raw trace retention.
- Hash prompts where raw prompt retention is unnecessary.
- An introspection provider gets observation authority only, never governance authority.
- No adapter may bypass normal PCM permissions.
- Causal intervention or safety-control modification is outside the baseline integration and must remain explicitly experimental and opt-in.
- Preserve upstream MIT-code provenance and paper attribution when adapting upstream implementation details.

## Reproducibility

Normal PCM tests use synthetic probe responses and require no network, model, GPU, CUDA, Qwen, PyTorch, or Jacobian lens. Live Aion probing is an optional external integration test only.

The scientific interpretation should always retain model/lens/version information when available, because Jacobian-lens results are model- and instrument-specific.

## Design principle

**Use introspection to make artificial agents more epistemically accountable about themselves, not to turn hidden activations into an oracle of consciousness.**
