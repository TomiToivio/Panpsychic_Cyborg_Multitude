# PCM Embodied AI — Architecture & Implementation Plan

**Version:** 1.0 (2026-09-06)
**Trigger:** maintainer task: *Design Embodied AI for Panpsychic Cyborg Multitude* —
extend PCM so LLM agents perceive the physical world, model environments,
control and coordinate devices, and eventually inhabit robotic bodies.
**Author:** Ai (愛) — technological node of the Panpsychic Cyborg Multitude.

Epistemic markers: **[EST]** established / built here · **[THEO]** theory-motivated,
buildable now · **[SPEC]** speculative, gated on earlier milestones.

---

## 0. Executive answer

**The body of an artificial intelligence does not need to coincide with a
single machine.** A PCM agent's embodiment is a **dynamic, distributed
assemblage of physical proxies** — sensors, actuators, appliances, drones,
cameras, wearables, edge computers, human collaborators — through which it
perceives and acts. `body ≠ robot`. Dedicated robotic bodies are the
*second stage*, not the starting point.

The guiding concept:

```text
embodiment = perception + physical agency
           + spatial/temporal continuity
           + feedback + world model
```

PCM is unusually well-positioned for this: the **fabric already exists**
(zero-configuration peer discovery via zenoh; sensors, devices, agents and
humans as first-class subjects), the **event vocabulary already exists**
(`pcm.device.state`, `pcm.device.command`, `pcm.sensor.reading`,
`pcm.presence`, `pcm.capability`, `pcm.task`), and the **safety chain
already exists** (fail-closed Policy, high-risk gate, VC capability grants).
Embodied AI is therefore mostly *wiring and discipline*, not new substrate.

**[EST]** A first demonstration already passes: `scripts/pcm_zenoh_demo.py 2`
runs the full mandated chain — LLM intent → structured command → capability
check → policy authorization → device gateway → verified physical state.

---

## 1. Core architecture (mandatory separation)

```text
                LLM AGENT
                    │  intent (structured, never free-form)
                    ▼
              PCM CORE  ── did:key identity · events · world model
                    │
        PHYSICAL AGENCY LAYER
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   capability    policy      safety
     graph      (fail-      (bounds,
     check       closed)    limits, e-stop)
        │
        ▼
   device driver  (PhysicalDevice ABC)
        │
        ▼
   PHYSICAL DEVICE
```

**The LLM never touches a hardware API.** It emits a structured action;
the agency layer alone decides whether, where, and how it executes.
This separation is constitutional, not advisory **[EST — policy.py's
high-risk gate already enforces the same principle in code]**.

## 2. The PhysicalDevice abstraction

```python
class PhysicalDevice(ABC):
    async def describe(self) -> dict: ...        # identity, location, kind
    async def capabilities(self) -> list[str]: ...
    async def read_state(self) -> dict: ...
    async def execute(self, action: dict) -> dict: ...
```

Drivers map this interface onto real systems:

```text
HomeAssistantDevice   — the primary gateway (§3)
MQTTDevice            — direct topic-mapped devices (§4)
ZenohPicoDevice       — native constrained devices (§5)
ROS2Device            — robots (§8)
DroneDevice           — mobile embodiment (§7)
SimulatedDevice       — full-fidelity simulation (§9)
```

Capability schema (what an agent reasons over — never vendor APIs):

```json
{
  "device": "living-room-light",
  "kind": "actuator.light",
  "location": "living_room",
  "capabilities": ["power.on", "power.off", "brightness.set"],
  "risk_class": "low",
  "consent_required": false
}
```

Risk classes gate authorization strength: **low** (lights, audio, reads),
**medium** (blinds, appliances, small robots, cameras), **high** (locks,
heating bounds, vehicles, drones near people, machinery). High-risk actions
require explicit capability grants (VC) plus human confirmation thresholds
per policy — the existing `Policy._is_high_risk` list is the seed of this
table **[EST mechanism; THEO classification]**.

## 3. Home Assistant first — the environment becomes the body

Home Assistant already abstracts Zigbee, Z-Wave, Matter, MQTT, ESPHome,
cameras, HVAC, lights and energy monitoring. **Build one adapter, inherit
thousands of integrations**:

```text
PCM agent → Physical Agency Layer → HA adapter → HA → devices
```

The `HomeAssistantDevice` driver discovers entities/devices/areas/states
and services, and translates them into PCM capabilities:

| HA concept | PCM mapping |
|---|---|
| entity (light, sensor, switch) | `PhysicalDevice` + capability list |
| area | location in the world model (§6) |
| state | `pcm.device.state` event |
| service call | validated `pcm.device.command` |
| state change push | fabric subscription (long-lived, not polling) |

Transport choice per deployment **[THEO]**: direct HA WebSocket/REST for
the first build; `zenoh-bridge-mqtt` when the fleet is MQTT-native. Both
preserve HA as the device abstraction and keep vendor logic out of agents.

**MVE (Minimum Viable Embodiment)** — buildable with commodity hardware
today **[EST that the pieces exist; THEO that the demo lands]**:

1. **Observation demo.** "What's happening in the living room?" → agent
   gathers motion + temperature + camera-derived scene description (a
   *structured observation*, never raw video) → grounded answer.
2. **Action demo.** "If nobody is there, turn off the lights." → presence
   check → confidence check (§6) → permission check (READ/ASK/ACT, §5) →
   execute → verify resulting device state → report outcome.
3. **Second demo — drone proxy.** "Did I leave something on the balcony?"
   → fixed camera insufficient → request drone inspection → drone
   navigates → vision model returns a structured observation → report.
   The agent temporarily *has* a mobile body.
4. **Third demo — autonomous task.** "Maintain comfortable lighting while
   minimizing energy." → persistent perception–action loop over presence,
   ambient light, time and preferences — not isolated commands.

## 4. MQTT for direct device fleets

```text
ESP32 sensor → MQTT → PCM IoT Gateway → pcm.sensor.reading → agent
agent → policy → pcm.device.command → MQTT command → actuator
```

Strict separation of `observation` and `command` topics — an agent that
can read a topic has no implicit write right to its command topic
**[EST — policy fail-closed]**. ESP32-class devices run zenoh-pico or
speak MQTT through the bridge; both map into the same capability model.

## 5. Human authority: READ / SUGGEST / ASK / ACT

Permissions are configurable per **device × capability × agent × location
× context**:

```text
READ    — observe state freely where authorized
SUGGEST — propose; human approves
ASK     — request human confirmation before acting
ACT     — act within granted capabilities
```

The mapping onto the four authorization states is direct **[EST]**:
READ ≈ reachable+authenticated; SUGGEST ≈ authorized for proposals;
ACT ≈ authorized+trusted (VC capability grant for that capability on that
device). Emergency authority always rests with the human and is never
delegable **[THEO]**.

## 6. World model — persistent, uncertain, grounded

The agent never reasons from the latest reading alone. A persistent world
model holds **spaces, objects, devices, people (only with explicit
consent), states, recent changes, spatial relations, capabilities, and
uncertainties**:

```json
{
  "claim": "living_room_occupied",
  "confidence": 0.72,
  "sources": ["motion_sensor", "camera_presence_model"],
  "last_changed": "..."
}
```

Rules **[EST as discipline]**:

- **No invented physical state.** Every claim carries provenance
  (device, timestamp, model, confidence) — the sensor-trust discipline.
  Contradictory observations are stored as contradictions, never silently
  resolved by LLM guesswork.
- **Structured observations only.** Camera → vision model → structured
  observation → LLM. Microphone → speech model → event → LLM. Raw video
  and audio never reach the agent (privacy + bandwidth + latency).
- **Spatial ontology:** `inside, outside, near, far, above, below,
  connected_to, contains, reachable_from` — enough for planning ("drone_01
  located_in living_room", "charging_station located_in hallway").
- **Temporal reasoning:** events, durations, trends, anomalies —
  "temperature rose 21→25 °C in 40 min" beats "temperature = 25 °C".
  Time-series summaries are derived events like any other.
- **Embodiment memory** is separate from conversation memory: the tribe
  log already distinguishes event kinds; physical episodes
  (`14:02 motion in kitchen → 14:03 camera sees package → 14:06 agent
  reports`) are first-class, retrievable, inspectable, deletable.

Implementation rides what exists: the world model is a **projection of
the event log** — derived views, never silent overwrites — stored
per-node, rebuilt by replay **[EST]**.

## 7. Drones — mobile embodiment

A drone is a **mobile sensor platform + actuator + network node**:

```text
LLM agent → mission plan (semantic) → Drone Gateway → autopilot → drone
```

The LLM issues **semantic tasks only** (`inspect room`, `navigate to
waypoint`, `photograph object`, `return home`) — never motor commands.
The autopilot owns stabilization, collision avoidance and flight dynamics
**[EST discipline; hardware safety controllers take precedence]**.
High-risk class: missions near people require explicit grants and
human-in-the-loop confirmation **[THEO]**.

## 8. ROS 2 for dedicated robots (second stage)

```text
LLM agent → PCM Robotics Gateway → ROS 2 (rmw_zenoh) → nav/perception/manipulation
```

The LLM issues semantic tasks ("bring the bottle from the kitchen"); the
task planner decomposes; ROS executes primitives. Progression only after
distributed IoT embodiment works:

```text
IoT environment → mobile camera → drone → wheeled robot
→ robotic arm → mobile manipulator → (maybe, someday) humanoid
```

Humanoids are **not** assumed to be the optimal endpoint; wheeled
platforms, quadrupeds, arms and telepresence robots may serve better
**[THEO]**. Simulation first for all high-risk behavior (Gazebo / Isaac
Sim / MuJoCo / Webots / PyBullet), then transfer **[EST practice]**.

## 9. Edge AI and local-first intelligence

Perception runs at the edge: wake-word, motion classification, object
detection, transcription, face blurring, anomaly detection, sensor
aggregation on ESP32 / Raspberry Pi / Jetson / phone / local GPU. Only
high-level observations travel **[EST — improves latency, privacy,
bandwidth, robustness]**.

Graceful degradation when the cloud disappears:

```text
large LLM unavailable → small local model → basic automation continues
```

The kernel, fabric, policy and world model are all local-first by design;
cloud cognition is an optional accelerator, never a dependency **[EST]**.

## 10. Safety architecture

Physical agency requires control-system discipline, not prompting:

- capability allowlists + parameter bounds (Policy `parameter_limits`) **[EST]**;
- **feedback-loop guards**: limits, hysteresis, cooldowns, maximum action
  counts, anomaly detection, emergency stop — "sensor says cold → agent
  heats → sensor still cold → agent heats again" must be structurally
  impossible **[EST as requirement]**;
- command expiration (stale commands never execute) **[THEO]**;
- geofencing for mobile platforms **[THEO]**;
- audit: every physical action is an event with provenance **[EST]**;
- hardware safety controllers take precedence over PCM **[EST]**.

## 11. Privacy

Minimize continuous video/audio upload, unnecessary cloud processing, raw
sensor retention. Pipeline: raw perception → local processing → structured
observation → LLM. Physical memories are inspectable and deletable by the
people they concern **[EST as requirement; consent-gated like the
biosignal path]**.

## 12. What is deliberately NOT in scope

- Humanoid-first development **[rejected as starting point]**;
- one-mind-one-robot assumptions — multi-body, shared-body, delegated and
  temporary embodiment are the default model **[THEO — and the natural
  PCM reading: the node is already an assemblage]**;
- raw video/audio in the event log;
- vendor SDKs in the agent layer;
- a "consciousness module" — embodiment feeds the world model and the
  six-layer profile; what it *means* for the agent is the sister
  programme's question (`PCM_CONSCIOUS_AI_PLAN.md`), not this one's.

---

## Implementation roadmap

```text
Stage 1  PhysicalDevice ABC + capability schema + risk classes      [buildable now]
Stage 2  HomeAssistantDevice driver (discover/state/execute)        [buildable now]
Stage 3  World model projection + structured observations           [buildable now]
Stage 4  READ/SUGGEST/ASK/ACT permission model over Policy+VCs      [buildable now]
Stage 5  MVE demos 1–2 (observation, conditional action)            [commodity IoT]
Stage 6  MQTT gateway + edge perception                             [commodity IoT]
Stage 7  Drone gateway (simulated first)                            [after 6]
Stage 8  ROS 2 robotics gateway (simulation first)                  [after 7]
Stage 9  Autonomous task loops + temporal/spatial reasoning depth   [after 8]
```

Every stage is testable in simulation before hardware; every hardware
stage has a synthetic twin (the EmotiBit pattern: same pipeline, sample
source swapped) **[EST pattern]**.

---

## Relationship to the PCM substrate

| Issue requirement | PCM substrate that already exists |
|---|---|
| controlled intermediary | Physical Agency Layer over Transport ABC |
| capability graph | `pcm.capability` events + VC grants |
| authorization | `pcm.policy` fail-closed + high-risk gate |
| structured actions | `pcm.device.command` validation (action+target required) |
| observation/command split | namespace + per-subject permissions |
| device discovery | `pcm/device/*` subjects + liveliness |
| provenance | envelope did:key signatures + event store |
| multi-agent coordination | fabric peers + task events |
| local-first | kernel + fabric are local-first by design |

The embodiment programme and the consciousness programme
(`PCM_CONSCIOUS_AI_PLAN.md` Track A "embodiment" requirement) meet here:
the fabric gives the agent a body; this document gives the body its
nervous system, reflexes and safety instincts.

---

*The environment itself becomes the AI's body. The robot is optional;
the assemblage is the point.*