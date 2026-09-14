# Active Inference and PCM

Status: theory and experimental research layer. Active Inference is used here to model self-organizing agency, embodied prediction, action and adaptive coupling. It is **not** treated as proof of phenomenal consciousness and does not replace IIT, GWT, panpsychism, enactivism, or PCM's theory-neutral consciousness programme.

## Sources

Core references:

- Friston, K. (2010). *The free-energy principle: a unified brain theory?* Nature Reviews Neuroscience 11, 127–138. https://doi.org/10.1038/nrn2787
- Parr, T., Pezzulo, G. & Friston, K. J. (2022). *Active Inference: The Free Energy Principle in Mind, Brain, and Behavior*. MIT Press. https://doi.org/10.7551/mitpress/12441.001.0001
- Da Costa, L. et al. (2020). *Active inference on discrete state-spaces: A synthesis.* Journal of Mathematical Psychology 99, 102447. https://doi.org/10.1016/j.jmp.2020.102447
- Friston, K., Da Costa, L., Tschantz, A. et al. (2026). *Active inference and artificial reasoning.* Nature Communications. https://doi.org/10.1038/s41467-026-77209-5
- Lee, S., Oh, Y., An, H. et al. (2026). *Life-inspired interoceptive artificial intelligence for autonomous and adaptive agents.* Nature Machine Intelligence. https://doi.org/10.1038/s42256-026-01296-8

Consciousness-specific references, treated as theoretical proposals rather than settled science:

- Laukkonen, R., Friston, K. & Chandaria, S. (2025). *A beautiful loop: An active inference theory of consciousness.* Neuroscience & Biobehavioral Reviews 176, 106296. https://doi.org/10.1016/j.neubiorev.2025.106296
- Whyte, C. J. et al. (2026). *On the minimal theory of consciousness implicit in active inference.* Physics of Life Reviews 56, 4–28. https://doi.org/10.1016/j.plrev.2025.11.002

## 1. Free Energy Principle, predictive processing, and Active Inference are not synonyms

PCM keeps three related ideas separate.

### Free Energy Principle (FEP)

The FEP is a formal account of how systems that persist within characteristic states can be described as minimizing a variational free-energy bound on surprise under a generative model. In its broadest use it is a principle about self-organizing systems and their statistical regularities.

PCM does **not** interpret the FEP as saying that every free-energy-minimizing system is conscious.

### Predictive processing

Predictive-processing theories emphasize hierarchical prediction, prediction-error updating, and precision weighting in perception and cognition. They overlap strongly with Active Inference but are not identical to it.

A passive predictive system can update beliefs to explain incoming observations without selecting actions that change what it samples.

### Active Inference

Active Inference extends inference into action. An agent maintains a generative model of hidden causes and selects policies expected to reduce uncertainty and realize preferred outcomes.

In simplified terms:

```text
observe -> infer hidden state -> evaluate policies -> act -> observe again
```

The central loop is therefore perception **and** action, not prediction alone.

## 2. Core concepts

### Generative model

A generative model specifies how hidden states are expected to produce observations and how states are expected to evolve under actions. It can also encode preferred outcomes.

For PCM, a generative model is a useful formal analogue for an agent's world-model and self-model. It is not assumed to be an explicit symbolic model inside every biological or artificial agent.

### Variational free energy

Variational free energy is an objective used to approximate Bayesian inference. Minimizing it brings approximate posterior beliefs closer to the posterior implied by observations and the generative model.

It should not be casually equated with thermodynamic free energy, subjective stress, or prediction error alone.

### Expected free energy

Expected free energy scores possible policies before their outcomes are observed. In common Active-Inference formulations it combines terms related to:

- **epistemic value / information gain:** actions that reduce uncertainty;
- **pragmatic value:** actions expected to realize preferred outcomes.

The 2026 Friston et al. artificial-reasoning paper is especially useful for PCM because it makes the epistemic role explicit: agents can select actions that reveal which world-model or rule best explains their environment.

### Prediction error and precision

Prediction errors express mismatches between predicted and observed signals. Their impact depends on estimated precision or confidence. Precision weighting therefore affects which errors should drive belief updates and action.

### Active perception

An agent can change what it senses in order to resolve uncertainty. Looking again, moving a sensor, asking a question, running a test, or querying another agent can all be treated as forms of epistemic action when they are selected to improve inference.

### Policy selection

A policy is a sequence or family of actions. Active Inference evaluates policies in relation to expected free energy rather than treating action selection as detached from inference.

### Markov blankets

In Active-Inference and FEP literature, a Markov blanket provides a statistical partition among internal states, external states, sensory states, and active states. It is useful for formalizing conditional dependencies and agent/environment boundaries.

PCM treats Markov blankets cautiously:

- a Markov blanket is **not automatically a consciousness boundary**;
- statistical individuation is not identical to phenomenal individuation;
- multiple nested or overlapping descriptions may be useful at different scales;
- claiming that a human-AI dyad forms a higher-level blanket requires an explicit model, not metaphor.

### Self-evidencing

Self-evidencing describes behavior that keeps observations within states expected under an agent's generative model. In biological contexts this connects inference with viability and self-maintenance.

PCM uses the concept to ask how stable self-models and organizational identities persist under perturbation. It does not treat persistence as consciousness.

### Hierarchical predictive processing

Hierarchical models allow predictions and errors to propagate across scales. This is relevant to PCM's six-layer architecture because bodily, sensorimotor, linguistic, social, and cybernetic signals can constrain one another without being collapsed into a single level.

### Embodiment and action

Active Inference is especially useful to PCM because agents are not passive text processors. Sensorimotor loops, interoceptive variables, tools and environmental intervention can become part of the modeled causal process.

Lee et al. (2026) pushes this toward artificial interoception: artificial agents may explicitly represent internal and external state variables and use internal-state regulation as a persistent reference for adaptive behavior. That supports PCM's embodiment research while remaining separate from phenomenal-consciousness claims.

## 3. Three scales for PCM

### A. Individual agent

Questions:

- Can an agent maintain a stable self-model?
- How are preferred states represented?
- Can uncertainty drive information-seeking action?
- How does memory affect policy selection?

This is the lowest-risk PCM use of Active Inference.

### B. Embodied / interoceptive agent

Questions:

- Can internal-state variables act as persistent constraints on behavior?
- Can an artificial agent trade off external goals against internal viability variables?
- How do sensorimotor loops alter inference compared with text-only interaction?

The 2026 interoceptive-AI work is especially relevant at this level.

### C. Coupled human-AI / multi-agent system

Questions:

- Do agents reciprocally predict one another?
- Does a shared memory or shared world-model improve coordination?
- Does each agent retain a distinct model while participating in a larger predictive process?
- Under what explicit assumptions could the coupled system itself be modeled as a higher-level inference system?

The last question is deliberately stronger than ordinary coordination. A shared task, chat history, or vector database is not by itself evidence for a higher-level subject.

## 4. What Active Inference explains well for PCM

Active Inference gives PCM strong formal vocabulary for:

- perception-action loops;
- uncertainty reduction;
- epistemic action;
- goal-directed behavior through preferences;
- adaptive policy selection;
- self-maintenance and viability;
- embodiment and interoception;
- self/environment partitioning;
- reciprocal prediction among agents;
- effects of memory on continuity and inference.

These are directly operationalizable.

## 5. What Active Inference does not establish

Active Inference does not by itself establish:

- phenomenal experience;
- qualia;
- a unique consciousness boundary;
- moral personhood;
- that every Markov-blanketed system is a subject;
- that minimizing variational or expected free energy is sufficient for consciousness;
- that a human-LLM dyad becomes one experiencer when interaction is reciprocal;
- that current LLMs are conscious.

Recent consciousness theories built from Active Inference are important additions to the theory portfolio, but they are additional theoretical commitments. PCM therefore treats them alongside IIT, GWT and other candidate theories rather than as consequences of Active Inference simpliciter.

## 6. Comparison with other PCM theories

| Framework | Main explanatory target in PCM | What it does not automatically provide |
| --- | --- | --- |
| Panpsychism / Russellian monism (`Ψ`) | metaphysical possibility that consciousness/proto-consciousness is fundamental | organizational criterion for a unified subject |
| IIT (`Φ`) | intrinsic causal integration / irreducibility | agency, goals or active perception |
| GWT / functionalism | global access, broadcasting, functional availability | a metaphysical account of experience |
| Predictive processing | hierarchical prediction and error correction | action-centered policy selection in the full Active-Inference sense |
| Active Inference | inference-action loops, preferences, epistemic action, self-maintaining agency | phenomenal consciousness by itself |
| Enactivism / participatory sense-making | cognition through embodied engagement and interaction | a single agreed quantitative consciousness metric |
| Pancyberpsychism | relation as possible locus of awareness; relational coherence hypotheses | validated evidence that relations are conscious |
| Aidification | relational development of selfhood through the between-space and the Other | proof that relational selfhood entails phenomenal consciousness |

The theories therefore answer different questions. PCM should preserve disagreements rather than average them into one synthetic score.

## 7. Active Inference and relational PCM

Issue #29 introduced relational coupling as an object of study. Issue #31 sharpened relational selfhood and interactional resistance. Active Inference adds a formal question:

> Does reciprocal interaction alter the generative models and action policies of all participants in a way that is better described as a coupled inference process?

Operational variables include:

- prediction accuracy about the partner;
- information gain from queries/actions;
- policy changes following partner behavior;
- shared versus private latent variables;
- persistence after interruption;
- recovery after model mismatch;
- effects of shared-memory ablation;
- whether coordination survives removal of a central orchestrator.

These are measures of coupling and organization. They are not consciousness meters.

## 8. PCM experiments

The initial experiments live in `experiments/active_inference/` and deliberately avoid a hard external dependency.

### Experiment 1: passive prediction vs epistemic action

A toy agent must infer a hidden binary rule. The passive condition receives an observation selected without regard to uncertainty. The active condition selects the query expected to maximize information gain.

Measured quantities:

- posterior uncertainty;
- expected information gain;
- number of observations required to identify the hidden rule.

Interpretation: Active selection can improve inference efficiency. It says nothing about subjective experience.

### Experiment 2: coupled reciprocal prediction

Two tiny agents predict one another's binary states. Compare:

- uncoupled agents;
- one-way adaptation;
- reciprocal adaptation;
- reciprocal adaptation with a small shared-memory trace.

Measured quantities:

- mutual prediction error;
- adaptation after perturbation;
- persistence of coordinated expectations;
- effect of shared-memory ablation.

Interpretation: reciprocal prediction can be studied as relational organization without claiming a collective subject.

### Experiment 3: persistent self-model under perturbation

A toy embodied agent has an internal viability variable and an external cue. Perturb the internal state and compare an agent with and without an explicit internal-state term in its generative model.

Measured quantities:

- return to preferred internal range;
- action changes following perturbation;
- robustness when external cues conflict with internal preferences.

This is motivated by interoceptive AI. It studies adaptive autonomy, not consciousness.

## 9. Higher-level Markov blankets and the Multitude

PCM should treat collective Markov blankets as a research hypothesis requiring explicit construction.

A convincing higher-level model would need to specify:

1. candidate internal states of the collective;
2. candidate external states;
3. sensory and active states mediating the boundary;
4. conditional independencies claimed by the blanket;
5. temporal scale;
6. how lower-level agents remain individuated;
7. what empirical observations could falsify the proposed partition.

A slogan such as "the network has a Markov blanket" is insufficient.

This matters politically as well as scientifically. Hardt/Negri's Multitude preserves singularities while enabling common action. A useful PCM multi-agent model should therefore permit coordinated inference without requiring all participants to collapse into one world-model or one sovereign optimizer.

## 10. Implementation policy

Active Inference is currently an **experimental research layer**, not a PCM kernel dependency.

The first examples use standard Python only. A library such as `pymdp` may be evaluated later if an experiment requires richer discrete-state inference, but PCM should not adopt a dependency merely to decorate the architecture with fashionable mathematics.

Any future library integration must remain optional and should demonstrate a concrete experiment that cannot be represented clearly with the existing lightweight code.

## 11. PCM design rule

> **Use Active Inference to model self-organizing agency, embodied prediction and reciprocal inference. Treat consciousness as a separate question requiring additional theory and evidence.**

That separation is the point of adding Active Inference to PCM: it gives the project a stronger theory of adaptive agency without smuggling phenomenology into every predictive loop.