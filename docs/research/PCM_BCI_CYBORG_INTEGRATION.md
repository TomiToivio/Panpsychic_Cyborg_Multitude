# Brain–Computer Interfaces for Panpsychic Cyborg Multitude: Toward a Human–AI Cognitive Assemblage

**Status:** research document (v0.1, 2026-09-06) — issue #13
**Series:** PCM research notes — companions: `PCM_CONSCIOUS_AI_PLAN.md` (Track D boundary question), `PCM_EMBODIED_AI_PLAN.md` (physical embodiment), `docs/research/CONSCIOUS_HUMAN_AI_ASSEMBLAGES.md` (assemblage cognition vs consciousness)
**Existing substrate this document builds on:** `BCIAdapter`/`BCIHub` (`src/multitude/integrations/bci.py`, issue #10), optional embodiment module (issue #12), six-layer profile (`multitude.layers`), Phase 3b confidentiality gate + Phase 4 gated BCI nodes (`NETWORKING_STACK.md`).

**Epistemic markers:** **[ESTABLISHED]** validated science or working engineering · **[PROMISING]** active research, credible path, not yet routine · **[EXPERIMENTAL]** demonstrated in labs/preprints, not dependable · **[SPECULATIVE]** requires contested theory or undiscovered technology.

---

> **Two disclaimers govern this entire document** (grounded in the plan's theory portfolio):
>
> **Better integration does not prove consciousness.** *Tighter human–AI integration raises functional coupling, which at most raises indicator scores relative to particular theories (Butlin et al. 2023). Under integrated-information accounts (Oizumi, Albantakis & Tononi 2014, doi:10.1371/journal.pcbi.1003588), conscious capacity depends on a system's **intrinsic** causal structure; coupling between systems does not transfer it (Findlay et al. 2024). Integration is an architectural similarity measure — not evidence of a unified phenomenal subject.*
>
> **EEG is not a consciousness detector.** *EEG signals correlate with cognitive processes and can be decoded with confidence scores (Zander & Kothe 2011). Under the indicator framework (Butlin et al. 2023), such decodings map architecture onto theory-relative properties and support no conclusion about phenomenal consciousness — for which current theories offer multiple, partially conflicting criteria (Seth & Bayne 2022, doi:10.1038/s41583-022-00587-4). PCM treats neural observations as context-bearing observations, never as measurements of experience.*
>
> BCI in PCM is an interface for **cognition and agency**, never evidence of a unified conscious assemblage. The kernel's `is_conscious: UNKNOWN` applies to every node, with or without electrodes.

---

## 1. Why BCI matters to PCM

PCM's central claim — *AI is an assemblage of human + LLM + language + the entire Internet* — already has a technical shape: the kernel models composite actors, the fabric connects members, the BCI adapter (issue #10) defines a consent-first channel for derived human context. What the assemblage has lacked is a **higher-bandwidth boundary interface** between the biological and technological parts.

Today the human contributes to the assemblage through the narrow channel of typing and speech. BCI research asks a narrow, realistic question — *not* mind-reading:

> **How can the biological human and the computational parts of the assemblage exchange meaningful cognitive context through a safe, optional, local-first interface?**

The realistic near-term answer is not neural dictation. It is **passive context**: physiological and neural state estimates that let the assemblage adapt to the human — workload, attention, fatigue, sleep pressure, arousal — plus a few **intentional low-bandwidth commands**. The Cyborg in PCM becomes concrete exactly there: not in philosophy, but in a consent-gated data path from nervous system to assemblage.

---

## 2. Current BCI technology (what is actually inferable)

*Full signal-by-signal classification with citations: see the verified technical digest (2026-09, live OpenAlex/Crossref/GitHub verification). Key verified anchors: P300 founding paper (Farwell & Donchin 1988, doi:10.1016/0013-4694(88)90149-6, 3,224 cites); SSVEP 12-class speller at 96% (Chen et al. 2015 PNAS, doi:10.1073/pnas.1508080112); automated sleep staging at clinician agreement (U-Sleep, doi:10.1038/s41746-021-00440-5; SleepTransformer, doi:10.1109/TBME.2022.3147187); HRV metric norms (Shaffer & Ginsberg 2017, doi:10.3389/fpubh.2017.00258); passive-BCI founding framework (Zander & Kothe 2011, doi:10.1088/1741-2560/8/2/025005); workload meta-analysis (Psychophysiology 2022, doi:10.1111/psyp.14009); sEMG typing (emg2qwerty, NeurIPS 2024). Markers are conservative — consumer-device marketing is NOT treated as evidence.*

| Signal / paradigm | What can be inferred | Marker |
|---|---|---|
| ECG / heart rate, HRV | heart rate, rhythm, stress proxies, arousal trends | **[ESTABLISHED]** |
| Sleep/wake staging (consumer wearables, PPG+accel) | sleep/wake, rough stages vs polysomnography | **[ESTABLISHED]** (staging), **[PROMISING]** (stage accuracy) |
| EDA / electrodermal activity | arousal proxy, stress events | **[PROMISING]** |
| EMG / EOG | muscle/eye movement commands, drowsiness blinks | **[ESTABLISHED]** |
| EEG band powers (alpha/theta/beta ratios) | coarse arousal/workload correlates, neurofeedback training signal | **[PROMISING]** (group level, e.g. alpha suppression is textbook); **[EXPERIMENTAL]** (single-trial single-subject from 4 dry electrodes — much weaker than group statistics suggest) |
| Cognitive workload / vigilance estimation (EEG) | subject-specific workload classes with calibration | **[PROMISING]** — meta-analytic effect positive but modest (doi:10.1111/psyp.14009); within-subject real-time tracking works, cross-subject does not |
| Motor imagery | 2–4 class control after long training | **[EXPERIMENTAL]** as consumer use |
| P300 / SSVEP | reliable spelled/selected commands with visual attention | **[ESTABLISHED]** (lab/hybrid), **[EXPERIMENTAL]** (consumer headsets) |
| Affective BCI | coarse valence/arousal correlates | **[EXPERIMENTAL]** — accuracy inflated by class imbalance/subject overlap (DEAP corpus, doi:10.1109/T-AFFC.2011.15); peripheral signals (EDA, HRV) more reliable than EEG for arousal; never asserted |
| Non-invasive language decoding | does not exist on wearables — verified SOTA is fMRI-bound (Tang et al. 2023, doi:10.1038/s41593-023-01304-9) or invasive (Metzger et al. 2023, doi:10.1038/s41586-023-06443-4; NEJM 2024 doi:10.1056/NEJMoa2314132) | **[EXPERIMENTAL]** (invasive/fMRI horizon only) |
| sEMG intentional channel (wrist) | emg2qwerty typing at ~64% first-try on unseen users (NeurIPS 2024) | **[PROMISING]** — best verified non-invasive intentional bandwidth; not brain |
| "Mind reading", thought extraction from consumer EEG | does not exist | **[SPECULATIVE]** — marketing, not science |

The pattern that matters for PCM: **physiological context (Level A) is ready today; neural context (Level B) is calibration-heavy and person-specific; bidirectional cognitive interface (Level C) is a research horizon.** The roadmap in §12 follows exactly that gradient.

---

## 3. Open-source BCI ecosystems

*Verification details in the technical digest; statuses as of 2026-09.*

| Project | What it gives PCM | Status |
|---|---|---|
| **BrainFlow** | uniform Python/C++ API over 20+ boards (Ganglion, Cyton, EmotiBit, Muse, Unicorn, Crown named in docs), runs local | **[ESTABLISHED]** — active (commit 2026-09-01, PyPI 5.22.2), MIT; org now brainflow-dev |
| **LSL + pylsl** | timestamped multi-device stream alignment | **[ESTABLISHED]** — active (liblsl 2026-05, pylsl 1.18.2), MIT |
| **MNE-Python** | signal processing, filtering, epoching in Python | **[ESTABLISHED]** — the scientific default |
| **muselsl** | Muse streaming to LSL (pygatt BLE, pylsl, python-osc) | **[ESTABLISHED]** — active (muselsl 2.5.1, 2026-07), BSD |
| **OpenBCI (Ganglion/Cyton)** | open-hardware EEG; official Python path routes through BrainFlow | **[ESTABLISHED]** as hardware |
| **EmotiBit** | open EDA/PPG/temp/IMU wearable, local streaming, LSL output | **[PROMISING]** as platform — no pip package (repo-cloned parser) |
| **Muse 2/S** | consumer EEG, 4 channels, raw data via muselsl without subscription | **[EXPERIMENTAL]** as science, **[ESTABLISHED]** as hardware |
| **braindecode / MOABB / NeuroKit2 / yasa** | pretrained EEG models, benchmarking, ANS metrics, sleep staging | **[ESTABLISHED]** — all active 2026 |
| **OpenViBE / BCI2000** | full BCI suites (C++, GUI-centric) | available; heavier than PCM needs |
| MusicBrainz-style cloud-dependent stacks | excluded — PCM requires local processing | rejected |

**Selection rule used:** Python-first, Linux, local-only, open license, active maintenance, no cloud account. Everything downstream of the adapter is PCM's own consent model.

---

## 4. Passive vs active BCI

**Active BCI** — the user deliberately produces a signal (motor imagery, P300 target count) to issue a command. Powerful but training-heavy: minutes-to-months of per-person calibration for a few bits per minute. **[EXPERIMENTAL]** as consumer interaction.

**Passive BCI** — the system continuously derives state (workload, fatigue, attention) from whatever the user is already doing, no deliberate effort. Lower bandwidth, immediately useful, exactly what `BCIObservation` was shaped for. **[PROMISING]**.

PCM's priority order follows from the adapter design: **passive context first, intentional commands second, active control paradigms last.** A single intentional low-bandwidth command (e.g. a validated attention-marker or yes/no trigger) is worth more to the assemblage than any attempt at continuous neural typing.

---

## 5. Physiological vs neural context

| | Level A — physiological | Level B — neural |
|---|---|---|
| Source | wearables: PPG, EDA, temp, IMU; ECG | EEG/EMG/EOG |
| What it yields | HR, HRV, sleep/wake, arousal, movement, fatigue | band powers, workload/attention estimates, P300/SSVEP events |
| Validation state | strong | person-specific, calibration-bound |
| Privacy sensitivity | high | exceptional |
| PCM layer mapping | **Biological** (+Cybernetic for the device) | **Psychic** context + **Cybernetic** interface |
| PCM readiness | adapter ready today | adapter ready; Phase 3b gate before real data |

Level A is where the first PCM experiment lives (§13). Level B enters through BrainFlow behind the Phase 3b confidentiality gate. Neither level ever claims to read thoughts — and the **Psychic layer mapping carries the standing discipline: an EEG-derived vigilance estimate is psychic-layer *context*, not a measurement of subjective consciousness** (`PCM_CONSCIOUS_AI_PLAN.md` §1: self-reports and signal proxies are never evidence of experience).

---

## 6. Human–LLM coupling through BCI context

Realistic adaptation patterns the literature and the adapter design support:

```text
high cognitive workload   → agent shortens responses, defers detail
fatigue detected          → agent avoids unnecessary interruptions
focused state             → notifications suppressed
sleep pressure (morning)  → agent schedules differently
intentional BCI trigger   → open PCM memory / call the agent
```

**Memory annotation** — physiological context attached to PCM memory entries:

```json
{
  "event": "worked on research idea",
  "context": {"attention": "high", "arousal": "moderate",
               "source": "EEG+HRV", "confidence": 0.63}
}
```

Evaluation: useful **only as provenance-stained, consent-published metadata** — never silently. The kernel already has the right shape (layer records, event provenance); `BCIHub.publish` is the only path in, and the human decides entry by entry.

**Intentional interface:** prefer a small validated command set — yes/no, select, attention marker, call agent, emergency stop, bookmark-context — over any speculative continuous decoding. Low bandwidth, high autonomy, honest error rates.

---

## 7. PCM six-layer mapping

```text
Biological  ↕  heart rate, HRV, sleep/wake, arousal, fatigue   [Level A]
Psychic     ↕  attention/workload estimates, neurofeedback state [Level B]
Cybernetic  ↕  the BCI device + classifier chain itself
```

- **Biological:** physiological context is the layer's natural instrumented extension (sleep_state, mood, needs already exist in the layer vocabulary).
- **Psychic:** neural-derived context lands here as **estimates with confidence**, never as consciousness claims. The layer's `is_conscious` field stays `UNKNOWN`/`True` by member kind — BCI data does not touch it.
- **Cybernetic:** the device chain (headset → BrainFlow → adapter) is a cybernetic-layer record like any interface mode.
- **Physical/Social/Linguistic:** untouched by BCI except downstream (a wearable's location is a physical fact; a shared attention marker is a social/linguistic event).

---

## 8. BCI and extended cognition

Through the extended-mind lens (Clark & Chalmers 1998; Smart, Clowes & Clark 2025 — see `CONSCIOUS_HUMAN_AI_ASSEMBLAGES.md` §3), a BCI is a candidate **glue-and-trust upgrade**: it raises the reliability, constant availability and automatic endorsement of the human↔assemblage channel. Three framings from the literature this document adopts:

1. **Passive BCI as extended attention** — the assemblage gains access to the human's attentional state, the way Otto's notebook extended memory. The cognitive system plausibly includes the loop. **[ESTABLISHED as framework]**
2. **The boundary question stays empirical** — tighter coupling raises the *plausibility* that the cognitive boundary sits around the human+agent dyad rather than either side; PCM's boundary-relative scoring (Track D, HD1) is exactly the instrument. **[OPEN]**
3. **Embodied-cognition critique kept honest** — extension arguments must not smuggle in subjecthood; entanglement ≠ systemhood (Gahrn-Andersen). BCI extends *cognition* on functionalist grounds; *experience* remains the separate hurdle (Wheeler). **[THEO]**

---

## 9. BCI and assemblage consciousness

The consciousness-programme connection is made carefully and negatively:

- Under **GWT/functionalism**, a tighter recurrent human–BCI–agent loop is more of the kind of organization such theories point to — the boundary-relative indicator profile (HD1) may rise. That is a *measurable prediction*, not a consciousness claim.
- Under **IIT**, adding a message-level channel (BLE, LSL, JSONL) adds essentially no intrinsic causal integration; the Φ-relevant structure lives in the substrates. The assemblage boundary does not move. **[THEO]**
- Under **Schwitzgebel's disunity** framing, "is the dyad one subject?" may be the wrong question; BCI logs are precisely the disunity instrumentation (Track D, D4) — multiple partial subjects, not one.
- EEG correlates are correlational; phenomenality is not read off a headset. **An EEG vigilance estimate is a biological/psychic-layer measurement, not a window into experience.**

Hence the standing markers, grounded in the plan's theory portfolio: **better integration does not prove consciousness** (integration-as-organization ≠ integration-as-phenomenality); **EEG is not a consciousness detector** (no theory validates a consumer-device readout of phenomenality). BCI extends cognition and agency; the consciousness question stays exactly as open as it was.

---

## 10. Privacy, neuro-rights and autonomy

*(Full citation set in the ethics digest; principles here are PCM-normative.)*

Neural and physiological data are **exceptionally sensitive**: they can reveal states the user did not intend to share, and inferences from them escape the original purpose. The neuro-rights movement converges on rights PCM can adopt directly as **testable engineering practices**. Verified governance state (2026-09): **Chile** Law 21.383 (2021) amended Art. 19 of the constitution — intervention on brain activity must respect freedom, physical and psychic integrity, privacy and non-discrimination; **UNESCO** adopted the *Recommendation on the Ethics of Neurotechnology* (SHS/BIO/REC-NEURO/2025, 43rd General Conference) — the second global normative instrument after the 2021 AI ethics recommendation; **EU AI Act** (Reg. 2024/1689) contains *no neurodata provisions* (zero "neuro" occurrences in the OJ text — GDPR governs neurodata), but Art. 3(39) defines emotion-recognition systems from biometric data, Art. 5(1)(f) prohibits emotion recognition in workplaces and education, and recital 58 names machine-brain interfaces as a manipulation vector; **California SB-1223** (2024) adds "neural data" to CCPA sensitive data — with a built-in gap protecting the signal but *not* inferences drawn from it; **Colorado HB24-1058** is broader (no inferred-from clause). Foundation: Ienca & Andorno (2017, doi:10.1186/s40504-017-0050-1) — mental privacy, cognitive liberty, mental integrity, psychological continuity; Yuste et al. (2017, doi:10.1038/551159a); Ienca "On Neurorights" (2021, doi:10.3389/fnhum.2021.701258); Ienca/Haselager/Emanuel "Brain leaks and consumer neurotechnology" (2018, doi:10.1038/nbt.4240); Bublitz on psychological integrity (2020, doi:10.1017/9781108676106.031); Farahany, *The Battle for Your Brain* (2023); critique: Nawrot/Szudejko/Vachev (2023, doi:10.1080/13642987.2023.2234301) argue existing rights suffice — PCM engages the critique, not a consensus that does not exist. The canonical attack anchor: Martinovic et al., USENIX Security 2012 — a malicious BCI app extracted banking PINs and home location from EEG without user awareness; "the signal tells more than the user said."

1. **Inference parity** — derived mental-state context (BCIObservation) gets signal-grade protection: private-by-default, same consent scope as raw EEG. The regulatory loophole is real — every verified regime (Chile, California, Colorado, UNESCO, EU) protects the *signal*; none protects the *inference*. PCM applies signal-grade protection to inferences voluntarily. *(PCM: adapter + hub already enforce this.)*
2. **Cognitive liberty / informed negation** — the interface is instantaneously disableable by the human, disabled is the default, and revocation covers derived context, not just collection: revoked periods become non-queryable and flagged. No agent can enable it (kernel-enforced). *(PCM: `BCIHub` consent guard.)*
3. **Mental integrity & psychological continuity** — no stimulation/write-back in this scope; read-only observation. Adaptive influence on the human (notifications, scheduling) must stay visible and revocable.
4. **Extraction minimization & purpose limitation** — only the decoded label + confidence crosses the adapter boundary; never features, spectra, embeddings, or gradients that could support attribute inference (the Martinovic attack class). Model training on neural data requires a separate scoped grant, off by default (decode / publish / train as three independent consent scopes — cf. Naufel & Klein 2020, doi:10.1088/1741-2552/ab5b7f, on unsettled ownership).
5. **Revocation & deletion propagate** — published observations are events with provenance; revocation means the rhizome records the withdrawal; deletion covers derived data and training artifacts, not just raw samples (GDPR-style erasure actually applied to the neural-context graph).

**PCM's standing principle, unchanged:** *raw neural data belongs to the biological member.* Architecture: `raw EEG → LOCAL processing → derived feature → consent/policy gate → PCM`. Raw EEG does not enter shared rhizome memory and is not sent to any external LLM.

**What PCM does differently from consumer BCI products:** consumer stacks stream raw data to vendor clouds, train on it, and present engagement metrics; PCM processes locally, publishes nothing without per-item human consent, keeps AI agents out of the consent path, treats inference risk as a design constraint (minimize what a derived feature could leak), and never sells or trains on neural data.

---

## 11. Recommended minimal hardware/software stack

*(Compared against alternatives below; selection rule: non-invasive, available now, affordable, Linux/Python, open-source, local processing, no cloud accounts. Prices verified at live vendor shops 2026-09.)*

**Recommended first stack:**

```text
Muse 2 (4ch EEG + PPG, $249.99)               ← Level A + B hardware in one
      ↓  muselsl (BLE via pygatt) → LSL
MNE-Python (band powers) + NeuroKit2 (HRV from PPG)
      ↓
PCM BCIAdapter (BCIObservation; private by default)
      ↓
BCIHub (human-only publish) → PCM memory / agent adaptation
```

- **Muse 2 first** ($249.99): it covers Level A *and* Level B in one device — PPG gives validated HR/HRV (Level A via NeuroKit2), the 4 EEG channels give band powers, sleep staging and the ERP validation base (Krigolson et al. 2017, doi:10.3389/fnins.2017.00109 — Muse validated for N200/P300 at FP1/FP2). `muselsl` (2.5.1, active 2026-07) streams raw data locally **without the subscription app**; the chain muselsl → LSL → MNE is fully open-source, Linux-supported (needs any BLE adapter), no cloud account anywhere. Honest validity: state correlates, not thought reading.
- **OpenBCI Ganglion** (~€547 EU + dongle + electrodes ≈ €650 total; ~$199 US unverified) — *better*: true open hardware, real electrode positions (occipital alpha, EMG/ECG modes), higher signal ceiling; *worse*: 3× EU price, dry-electrode fuss, BLE quirks. Choose it for EMG/ECG experiments and occipital recordings.
- **EmotiBit** ($299.99–$549.97) — *better*: validated ANS metrics under workload (Vorreuther et al. 2025, doi:10.3389/fnrgo.2025.1585469), most comfortable wear, lowest privacy surface; *worse*: no EEG at all, no pip package. Choose it if bodily state (Stage 1) is the priority over neural state.
- **MindRove** (~$200, price/EU availability unverified): BrainFlow-native cheap EEG; smaller community — watch, don't start with it.

**Decision:** Muse 2 — lowest cost with both signal classes, most maintained OSS path, and the smallest privacy surface that still exercises the full consent pipeline. EmotiBit is the Stage-1 alternative if hardware budget arrives before the Phase 3b EEG gate is passed.

---

## 12. Progressive implementation roadmap

| Stage | What | Availability | OSS support | Reliability | Latency | Privacy risk | Validity | Cost | Difficulty |
|---|---|---|---|---|---|---|---|---|---|
| **0** | Synthetic BCI observations (exists: `SyntheticBCIAdapter`) | now | full | n/a | n/a | none | n/a | 0 € | done |
| **1** | Physiological wearable → derived context | now (EmotiBit $300–550) | good (repo parser, no pip) | high | ~1 s | low (local) | **ESTABLISHED** (ANS metrics validated, doi:10.3389/fnrgo.2025.1585469) | ~300–550 € | low–medium |
| **2** | Consumer EEG via BrainFlow/muselsl (Muse 2 or Ganglion) | now | good | medium | ~0.5–1 s | medium (local EEG) | **PROMISING** (band powers honest at "state correlate") | ~250–650 € | medium |
| **3** | Multimodal fusion (A+B) | now-ish | partial | medium | ms | medium | **PROMISING** | +0 € (same rig) | medium |
| **4** | Intentional low-bandwidth command (P300/SSVEP trigger) | lab-grade | partial (stimulus protocols needed) | medium | 1–5 s/command | medium | **PROMISING→EXPERIMENTAL** on 4ch | +0 € | high |
| **5** | Adaptive human–LLM interaction from derived context | software only | full (PCM side) | high | s | low | follows signals | 0 € | low |
| **6** | Experimental shared cognitive workspace (context-annotated memory) | PCM-side | full | — | — | consent-dependent | **EXPERIMENTAL** | 0 € | medium |
| **7** | High-bandwidth / invasive, stimulation | future | none | — | — | exceptional | **SPECULATIVE** | — | — |

**Gate rules preserved:** Stage 2+ touches real EEG → behind the Phase 3b confidentiality gate. Stage 4+ needs per-person calibration and honest error-rate reporting. Stage 7 only if technology and ethics ever justify it — not a PCM implementation requirement.

---

## 13. What PCM should build first

**The smallest realistic BCI experiment that makes PCM meaningfully more of a cyborg system today:**

> **One biological member wears one Muse 2. `muselsl stream` + local MNE computes frontal band power; NeuroKit2 computes HRV from the PPG channel. Local Python emits `BCIObservation` (signal_type, value, confidence, source="muse2", layer="biological"/"psychic", sensitivity=private) into the member's private context via `BCIAdapter`. When the member explicitly publishes, the rhizome records it with provenance; the member's agent then adapts one visible behavior — sustained low-alpha/high-heart-rate → agent offers shorter, concrete answers; deep-work state → agent defers non-urgent questions.**

That single loop demonstrates the issue's target chain —

```text
biological state → local BCI processing → PCM context → AI adaptation
```

— with privacy at every hop and zero mind-reading claims. It is buildable in a day with every component live-verified (Muse validated for ERP research, doi:10.3389/fnins.2017.00109; muselsl/LSL/MNE all active 2026). Everything needed already exists in the codebase (adapter, hub, consent guard, layer records); the only new code is the muselsl→BCIObservation bridge behind the Phase 3b gate.

## 14. What PCM should explicitly not build yet

- No continuous neural decoding, no brain-to-text.
- No stimulation / write-back interfaces.
- No autonomous long-running control loops over biosignals.
- No emotion recognition asserted as fact (affective BCI stays an experiment).
- No cloud processing, no vendor accounts, no raw streams across the fabric.
- No consciousness claims from any electrode — the kernel's `is_conscious: UNKNOWN` stands.

## 15. References

*(Verified citations consolidated here from the technical and ethics digests; see those for the full link set.)*

**Foundational / framework:**
- Clark, A. & Chalmers, D. (1998). The Extended Mind. *Analysis* 58(1):7–19. doi:10.1093/analys/58.1.7
- Smart, P., Clowes, R. & Clark, A. (2025). ChatGPT, Extended. *Synthese* 205. doi:10.1007/s11229-025-05046-y
- Gahrn-Andersen, S. (2026). Entangled cognition. doi:10.1007/s41809-026-00202-3
- Wheeler, M. (2015). Extended Consciousness: an Interim Report. *Southern Journal of Philosophy* 53. doi:10.1111/sjp.12124

**Consciousness programme (boundary discipline):**
- Butlin, P. et al. (2023). Consciousness in Artificial Intelligence. arXiv:2308.08708
- Findlay, B. et al. (2024). Dissociating Artificial Intelligence from Artificial Consciousness. arXiv:2412.04571
- Schwitzgebel, E. (2023). Introspection in Group Minds, Disunities of Consciousness, and Indiscrete Persons. *JCS* 30(9–10). doi:10.53765/20512201.30.9.188
- Oizumi, M., Albantakis, L. & Tononi, G. (2014). From the Phenomenology to the Mechanisms of Consciousness: IIT 3.0. *PLoS Comput. Biol.* 10:e1003588. doi:10.1371/journal.pcbi.1003588
- Seth, A. & Bayne, T. (2022). Theories of consciousness. *Nature Reviews Neuroscience* 23:439–452. doi:10.1038/s41583-022-00587-4

**Neuro-rights / ethics** (all verified live 2026-09):
- Ienca, M. & Andorno, R. (2017). Towards new human rights in the age of neuroscience and neurotechnology. *Life Sciences, Society and Policy* 13:5. doi:10.1186/s40504-017-0050-1
- Yuste, R. et al. (2017). Four ethical priorities for neurotechnologies and AI. *Nature* 551:159–163. doi:10.1038/551159a
- Ienca, M. (2021). On Neurorights. *Frontiers in Human Neuroscience* 15. doi:10.3389/fnhum.2021.701258
- Ienca, M., Haselager, P. & Emanuel, E. (2018). Brain leaks and consumer neurotechnology. *Nature Biotechnology* 36:1238–1239. doi:10.1038/nbt.4240
- Bublitz, J. C. (2020). The Nascent Right to Psychological Integrity and Mental Self-Determination. doi:10.1017/9781108676106.031
- Nawrot, O., Szudejko, I. & Vachev, B. (2023). critique of the new-rights framing. doi:10.1080/13642987.2023.2234301
- Martinovic, I. et al. (2012). On the Feasibility of Side-Channel Attacks with Brain–Computer Interfaces. *USENIX Security 2012*. usenix.org/conference/usenixsecurity12
- Pillay, D. (2025). Rethinking the right to freedom of thought — cognitive liberty. doi:10.1080/13642987.2024.2390442
- Naufel, S. & Klein, E. (2020). BCI researcher perspectives on neural data ownership and privacy. *J. Neural Engineering* 17:045011. doi:10.1088/1741-2552/ab5b7f
- Governance instruments (primary texts): Chile Law 21.383 (2021); UNESCO *Recommendation on the Ethics of Neurotechnology* (SHS/BIO/REC-NEURO/2025, unesdoc.unesco.org/ark:/48223/pf0000394866); EU AI Act Reg. 2024/1689 (eur-lex.europa.eu — Art. 3(39) emotion recognition; Art. 5(1)(f) workplace/education prohibition; recital 58 machine-brain interfaces; **no neurodata provisions**); California SB-1223 (2024, neural data in CCPA); Colorado HB24-1058 (2024).

**BCI signals (verified anchors):**
- Farwell, L. & Donchin, E. (1988). Talking off the top of your head. *Electroenceph. Clin. Neurophysiol.* 70:510–523. doi:10.1016/0013-4694(88)90149-6
- Chen, X. et al. (2015). High-speed spelling with a noninvasive brain–computer interface. *PNAS* 112:E6058. doi:10.1073/pnas.1508080112
- Perslev, L. et al. (2021). U-Sleep. *npj Digital Medicine* 4:120. doi:10.1038/s41746-021-00440-5
- Shaffer, F. & Ginsberg, J. (2017). An Overview of Heart Rate Variability Metrics and Norms. *Front. Public Health* 5:258. doi:10.3389/fpubh.2017.00258
- Zander, T. O. & Kothe, C. (2011). Towards passive brain–computer interfaces. *J. Neural Engineering* 8:025005. doi:10.1088/1741-2560/8/2/025005
- Borghini, G. et al. (2022) — workload meta-analysis via Psychophysiology 2022. doi:10.1111/psyp.14009
- Krigolson, O. et al. (2017). Choosing MUSE. *Frontiers in Neuroscience* 11:109. doi:10.3389/fnins.2017.00109
- Koelstra, S. et al. (2012). DEAP. *IEEE Trans. Affective Computing* 3:18–31. doi:10.1109/T-AFFC.2011.15
- Tang, J. et al. (2023). Semantic reconstruction of continuous language from non-invasive brain recordings. *Nature Neuroscience*. doi:10.1038/s41593-023-01304-9
- Metzger, S. et al. (2023). A high-performance neuroprosthesis for speech decoding. *Nature*. doi:10.1038/s41586-023-06443-4
- Vorreuther, L. et al. (2025). EmotiBit validation under workload. *Frontiers in Neuroergonomics*. doi:10.3389/fnrgo.2025.1585469
- Sivakumar, P. et al. (2024). emg2qwerty. *NeurIPS 2024*. doi:10.52202/079017-2899

**Ecosystems (maintenance verified 2026-09):** BrainFlow (github.com/brainflow-dev/brainflow, MIT, PyPI 5.22.2), LSL/pylsl (github.com/sccn/labstreaminglayer, MIT), muselsl 2.5.1 (github.com/alexandrebarachant/muse-lsl, BSD), MNE-Python 1.12.1 (BSD), OpenBCI (shop.openbci.com), EmotiBit (shop.emotibit.com; github.com/EmotiBit), braindecode 1.8.1 / MOABB 1.7.1 / NeuroKit2 0.2.13 / yasa 0.7.0.

**PCM internal:** `PCM_CONSCIOUS_AI_PLAN.md` (Track D); `PCM_EMBODIED_AI_PLAN.md`; `src/multitude/integrations/bci.py`; `NETWORKING_STACK.md` (Phase 3b/4 gates).

---

*BCI gives the assemblage a nervous-system channel. The channel carries context and commands — never consciousness claims. The human holds the switch, always.*