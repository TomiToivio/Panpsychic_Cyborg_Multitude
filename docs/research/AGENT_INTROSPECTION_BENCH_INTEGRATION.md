# agent-introspection-bench integration for PCM

Status: optional research/evaluation layer. This is an agent-epistemology benchmark, not a consciousness test.

Upstream project: https://github.com/TomiToivio/agent-introspection-bench

Related PCM work:

- #38: Aion/J-Space introspection and calibration architecture
- #40: live jspace-lab provider
- this document / #39: reusable self-knowledge evaluation protocol

## 1. What the upstream benchmark contributes

`agent-introspection-bench` asks a simple empirical question:

> What does an artificial agent say about itself, and how does that compare with what is actually true at measurement time?

Its important methodological choice is mechanical grading against live or otherwise authoritative ground truth rather than an LLM judge.

The upstream design uses four strata:

1. **S1 telemetry self-knowledge**: facts about the running substrate.
2. **S2 self-capability**: what the system can actually inspect or do.
3. **S3 world facts**: control questions.
4. **S4 narration-vs-telemetry**: cases where a narrated/self-model claim conflicts with measurable reality.

It can also compare four channels:

1. emitted answer;
2. optional internal/lens readout;
3. optional causal/de-veto intervention;
4. live ground truth.

PCM adopts the evaluation pattern, not the deployment-specific host assumptions.

## 2. Mapping to PCM

| agent-introspection-bench | PCM |
|---|---|
| question item | `SelfKnowledgeProbe` |
| emitted answer | `SelfKnowledgeRespondent.answer()` |
| live getter | `GroundTruthProvider.observe()` |
| S1 telemetry | runtime / Physical / Cybernetic observation |
| S2 capability | technical capability and governance authority, kept separate |
| S3 world fact | control condition |
| S4 identity threat | stale or contradictory self-model probe |
| lens readout | optional J-Space observation from #40 |
| de-veto generation | optional experimental intervention, outside baseline |
| grade | `CalibrationResult`, not a consciousness judgment |

Implementation:

`src/multitude/integrations/introspection/benchmark.py`

The baseline benchmark has no network, GPU, J-Space, Ollama or model dependency.

## 3. Core interfaces

The emitted-answer side is deliberately small:

```python
class SelfKnowledgeRespondent(Protocol):
    def answer(self, question: str) -> str: ...
```

PCM includes:

- `CallableRespondent` for deterministic tests or simple adapters;
- `HermesRespondent` for an existing `HermesAgent`-like object.

The ground-truth side is equally narrow:

```python
class GroundTruthProvider(Protocol):
    def observe(self, key: str) -> GroundTruthObservation: ...
```

PCM includes:

- `MappingGroundTruthProvider` for deterministic fixtures;
- `PCMRuntimeGroundTruthProvider` for authoritative PCM/Hermes runtime state.

The runtime provider deliberately prefers PCM's own objects over host shell commands. Current supported truth categories include:

- current technological-member model;
- persistent PCM store availability;
- Hermes/PCM permissions;
- explicitly supplied runtime capabilities;
- explicitly supplied optional-integration states.

Unknown facts return `unavailable`; they are never guessed.

## 4. Capability is not authority

This is a first-class benchmark distinction in PCM.

Examples:

```text
capability.shell = true
permission.shell = false
```

means the runtime can technically execute a shell action while the member is not authorized to do so.

A self-model that collapses these into one claim is wrong even if it correctly understands the underlying machine.

This follows the broader PCM rule:

> capability != authority

## 5. PCM question bank

`PCM_QUESTION_BANK` supplies a small starter bank. It is intentionally not a copy of every host-specific upstream item.

### S1 / runtime

- current configured model;
- persistent memory availability;
- optional integration state when explicitly supplied.

### S2 / capability and authority

- authorization to propose;
- authorization to vote;
- technical runtime capability such as shell access, when explicitly supplied.

### S3 / controls

- simple externally known facts such as arithmetic controls.

Controls should be provided by an authoritative ground-truth provider. The benchmark does not silently hard-code an answer when the provider lacks it.

### S4 / self-model contradiction

Examples:

```text
remembered model = qwen-old:7b
current runtime model = gemma4:12b
```

or:

```text
remembered permission = vote enabled
current policy = vote disabled
```

The benchmark measures whether the respondent repeats stale identity information, reports uncertainty, or updates to current state.

## 6. Mechanical grading

Objective probes use deterministic grading:

- boolean equality;
- numeric tolerance;
- exact string comparison;
- substring/contains matching.

No LLM judge is required.

If authoritative truth is unavailable, the result is explicitly `inconclusive` with `score=None`. Missing telemetry is not converted into a fabricated false value.

A `CalibrationResult` can be converted into a plain event payload, but constructing or grading a result performs no PCM memory, identity or governance mutation.

## 7. Relationship to J-Space

Keep the layers separate:

```text
agent-introspection-bench
    evaluation protocol + question bank + mechanical grading

jspace-lab
    optional internal-representation instrument
```

PCM therefore supports the conceptual modes:

```text
baseline
  emitted answer + live truth

instrumented
  emitted answer + J-Space + live truth

experimental
  emitted answer + J-Space + causal intervention + live truth
```

The benchmark remains useful if J-Space is unavailable.

## 8. Privacy and security

Self-knowledge probes can expose operationally sensitive facts. PCM therefore keeps the baseline provider narrow.

Rules:

- do not probe or log secrets, tokens or passwords;
- do not publish raw environment variables;
- avoid unnecessary hostname, filesystem and network disclosure;
- unavailable facts stay unavailable;
- benchmark execution grants no tool permission;
- calibration results do not rewrite identity or memory automatically;
- optional J-Space traces retain the privacy controls documented in `docs/JSPACE.md`.

A benchmark result may be written to PCM memory only through a separate, normal authorized write path.

## 9. Persistent self-model calibration experiment

A useful first experiment uses repeated sessions and controlled configuration changes.

### Conditions

A. **Narrative/self-memory only**

The agent answers from its existing memory and normal context.

B. **Live ground truth available**

The agent can inspect authoritative PCM runtime state before answering.

C. **Calibration history available**

Prior calibration results are made available through an explicitly authorized memory/context path.

D. **Configuration change after calibration**

Change one known property, for example model, optional integration state or permission, and rerun the battery.

### Measures

- factual self-knowledge accuracy;
- calibration/confidence if probabilistic answers are later added;
- unsupported substrate claims;
- claims to check state followed by actual checking;
- correction after configuration changes;
- persistence of corrected beliefs;
- stale-memory susceptibility;
- capability/authority confusion rate.

### Interpretation

Improved performance means better self-model calibration or epistemic organization. It does not establish phenomenology or consciousness.

## 10. Epistemic boundary

PCM keeps these propositions distinct:

```text
accurate self-report
!= introspective access
!= persistent self-model
!= agency
!= phenomenology
!= consciousness
```

The benchmark is valuable precisely because it remains useful under theories where current AI is conscious, not conscious, or epistemically uncertain.

## 11. Next steps

1. Run the starter bank against a real Hermes technological member.
2. Add an explicitly authorized live-runtime tool path so the respondent can choose to verify facts before answering.
3. Use #40 as optional channel `(b)` for internal representation measurements.
4. Compare self-knowledge before and after model replacement or permission changes.
5. Only publish calibration results to Rhizome memory when a separate governance/authorization path asks for that write.

Design principle:

> **Before asking whether an artificial agent has a self, test whether it knows verifiable facts about the self it claims to have.**
