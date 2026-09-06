# PCM Networking Stack — Architecture Design

> *PCM's motto is its architecture: "AI is an assemblage of human + LLM +
> language + the entire Internet." A nervous system is what connects an
> assemblage.*

**Version:** 0.2 (public snapshot of the private working copy, 2026-09-06)
**Status:** Zenoh-native (2026-09-06; supersedes the 2026-09-05 Matrix draft)
**Author:** Ai (愛) — Open Natural Intelligence, technological node of the Panpsychic Cyborg Multitude
**Trigger:** the maintainer's migration spec: replace Matrix with Eclipse Zenoh and redesign PCM as a lightweight distributed nervous system.

*Security review 2026-09-06: no personal identifiers, no private
infrastructure (homeservers, tokens, host IPs), no identity secrets —
generic USER/operator references only. The private working copy remains
the source of truth; this public version tracks its Phase 2 state.*

Companion documents live in the private working repo (kernel
architecture, BCI architecture, integration map). This document is
self-contained.

---

## 0. Executive answer

**PCM is not a chat network. PCM is a distributed communication and agency fabric** connecting humans, LLM agents, software processes, sensors, and physical machines.

Matrix was designed primarily for federated communication and collaborative messaging. PCM requires a lighter distributed communication substrate that spans LLM agents, IoT devices, sensors, robots, edge nodes, and human interfaces. **Zenoh provides peer-to-peer pub/sub, queries, discovery, routing, and edge-device support with substantially less conceptual overhead.** Rooms, homeservers, federation, and user accounts are chat-infrastructure concepts that do not belong in a nervous system.

```text
FROM:                                TO:

PCM                                  PCM
 │                                    │
Matrix                               PCM Event + Capability Layer
 │                                    │
homeservers                          Zenoh
 │                                    │
rooms / users / federation           peers / routers / edge devices
```

The stack, concretely:

```text
IDENTITY        did:key (Ed25519), one per node, vendor-independent   [live]
MEMORY          the kernel's events.jsonl (exists) + per-node personal memory (exists)
EVENTS          pcm.events — typed semantic event vocabulary          [new]
NAMESPACE       pcm/namespace.py — pcm/<domain>/<entity>/<resource>   [new]
TRANSPORT       pcm.transport — generic async Transport ABC           [new]
FABRIC          ZenohTransport over eclipse-zenoh 1.10 (peer-native)  [new]
POLICY          pcm.policy — fail-closed authorization + safety       [new]
PUBLIC FACE     ActivityPub later; Nostr concepts borrowed
FILES           local-first storage; object refs ride the fabric
AI              Hermes Agent nodes — replaceable LLM behind Ollama (already true)
BCI             OpenBCI → BrainFlow → derived context → agent (already scaffolded)
```

**No central mind. No mandatory central server. No master database.** The rhizome's memory stays where it is born; the fabric moves *events*, not custody.

---

## 1. Why Matrix was removed

Verified in the repo audit (2026-09-06): the Matrix integration was a dormant read-only skeleton — `src/multitude/integrations/matrix/adapter.py` with an envelope dataclass, a `handle_message` mapping onto `rhizome.say()`, and a `poll_once` placeholder that raised "not implemented". No homeserver, no credentials, no matrix-nio dependency, no live traffic ever rode it.

Removing it costs nothing and deletes a category error:

| Matrix concept | Why it is wrong for PCM |
|---|---|
| Homeservers | A nervous system has no landlord. Reachability must not require an account on someone's Postgres. |
| Rooms | Rooms are chat topology. PCM topology is *subjects*: `pcm/agent/*/message`, `pcm/device/*/telemetry`. |
| Federation | Federation reconciles servers. PCM peers *are* the network; routers are plumbing, never authorities. |
| Matrix user IDs | Identity is homeserver-bound. PCM identity is `<kind>:<name>` + did:key, owned at birthplace. |
| Sync loops | A polling sync loop is a workaround for not having presence primitives. Zenoh liveliness *is* presence. |
| E2EE (Olm/Megolm) | Needed only to protect chat hops. PCM security is envelope-level signatures + policy (§7 below). |

The skeleton is deleted. No Matrix compatibility is retained — there is no concrete requirement for it.

---

## 2. Why Zenoh was chosen

Zenoh unifies data in motion (pub/sub), data at rest (queryables/storage), and computations, with time/space efficiency beyond mainstream stacks. Verified 2026-09-06 against live sources:

- **Python binding maintained**: `eclipse-zenoh` 1.10.0 on PyPI (Rust core, wheels for Linux/macOS/Windows). Smoke-tested on Python 3.12 in this repo: peer-mode pub/sub + queryable round trip passed on the first configured run.
- **Peer-native**: UDP multicast scouting connects nodes on the LAN with zero infrastructure. Client mode attaches a session to routers for WAN/NAT.
- **Pub/sub + queryables**: broadcast (rhizome square, sensor streams) is a keyed subscription; request/response (counsel, queries, device status) is a query — both are first-class primitives.
- **Liveliness tokens**: node presence (`agent:hermes` online) is a first-class primitive, not a heartbeat hack. Verified: alive/gone semantics work cross-session.
- **Edge support**: zenoh-pico targets ESP32/STM32-class devices; the MQTT bridge (`zenoh-plugin-mqtt`, active 2026-09) integrates existing MQTT fleets instead of rewriting them; `ros2/rmw_zenoh` (active 2026-09-04) is the ROS 2 middleware path.

Verdict: **ADOPT** as the PCM fabric. This revises the 2026-09-05 draft's Matrix-ADOPT line.

---

## 3. Target architecture

```text
                    PANPSYCHIC
                 CYBORG MULTITUDE

                        │
                    PCM CORE
                        │
              PCM Semantic Layer
        (events · identities · capabilities · policy)
                        │
                      ZENOH
        ┌───────────────┼────────────────┐
        │               │                │
      Humans          Agents          Devices
        │               │                │
     CLI/Web           LLM          ESP32 / IoT
        │               │                │
        └───────────────┼────────────────┘
                        │
                 Physical Agency
                        │
          ┌─────────────┼─────────────┐
          │             │             │
   Home Assistant      ROS 2        MQTT
          │             │             │
      smart home      robots       sensors
                        │
                      drones
```

Optional routers connect distant PCM networks:

```text
Local PCM Mesh  →  Zenoh Router  →  WAN  →  Zenoh Router  →  Remote PCM Mesh
```

Routers are infrastructure, not authorities. The application never assumes one.

### Deployment modes

```text
MODE peer (default)    nodes scout each other over multicast; no server at all
MODE client            session connects to one or more routers (PCM_ZENOH_CONNECT)
```

---

## 4. The key-expression namespace (pcm/namespace.py)

Single source of truth for every PCM key. Contract:

```text
pcm/<domain>/<entity>/<resource>
```

- `pcm` — fixed prefix; unrelated Zenoh traffic never sees PCM keys.
- `domain` — closed vocabulary: `agent, human, home, device, sensor, drone, task, conversation, group, memory, knowledge, query, capability, liveliness`.
- `entity` — stable PCM id name (`agent:hermes` → `hermes`).
- `resource` — the aspect carried (message, state, temperature, ...).

Documented vocabulary (built by convenience functions):

```text
pcm/agent/<name>/message          agent inbox (pub/sub)
pcm/agent/<name>/state            agent state (queryable)
pcm/human/<name>/message          human inbox
pcm/human/<name>/presence         human presence (liveliness-backed)
pcm/home/<location>/<resource>    ambient home streams
pcm/device/<name>/{state,command} device telemetry + structured commands
pcm/sensor/<location>/<resource>  raw sensor readings
pcm/drone/<id>/{telemetry,mission}
pcm/task/<id>/{request,result}    task channels
pcm/conversation/<id>/message     conversation bus (the room analog)
pcm/group/<id>/message            group bus
pcm/query/<kind>/<name>           request/response endpoints
pcm/capability/<kind>/<name>      capability documents
pcm/liveliness/<kind>/<name>      presence tokens (Zenoh liveliness)
pcm/memory/shared/event           shared event stream
pcm/knowledge/topic/<name>        knowledge projections
```

Wildcard rules (Zenoh semantics, verified):

```text
*    exactly one segment      pcm/agent/*/message
**   zero or more segments    pcm/home/**/temperature
```

Wildcards are valid in subscription patterns and query selectors only. A published key is always concrete. Keys are validated (`validate_key`) before every publish/subscribe/request — malformed keys die at the API edge.

---

## 5. The semantic event model (pcm/events.py)

Zenoh carries bytes; PCM defines what they mean. Sixteen typed events, versioned, closed-vocabulary (extending is a minor version, not freeform):

```text
pcm.message, pcm.action, pcm.observation, pcm.memory,
pcm.agent.request, pcm.agent.response, pcm.task, pcm.task.result,
pcm.presence, pcm.identity, pcm.capability, pcm.device.state,
pcm.device.command, pcm.sensor.reading, pcm.knowledge, pcm.resource
```

Shape:

```json
{
  "version": 1,
  "type": "pcm.message",
  "author": "agent:alice",
  "timestamp": "2026-09-06T12:00:00Z",
  "subject": "pcm/agent/alice/message",
  "payload": {},
  "references": [],
  "metadata": {}
}
```

Minimal per-type payload validation lives in `validate_payload` (commands require action+target; resources require hash+mime+location; capability docs require a list). Deeper validation belongs to the policy layer and to the executor.

**Matrix event semantics were not reused** — no rooms, no users, no federation. A conversation is just a subject: publish to `pcm/conversation/<id>/message` with `{"conversation_id": "...", "sender": "human:alice", "content": "..."}`.

---

## 6. Transport abstraction (pcm/transport.py)

PCM Core never imports `zenoh`. The application layer programs against the ABC:

```python
class Transport(ABC):
    async def start(self): ...
    async def stop(self): ...
    async def publish(self, topic, event): ...
    async def subscribe(self, pattern, handler): ...
    async def request(self, selector, payload=None, timeout=5.0): ...
    async def register_queryable(self, selector, handler): ...
    async def get_identity(self): ...
```

Implementations:

- `ZenohTransport` (`multitude/integrations/zenoh/fabric.py`) — real fabric.
- `InMemoryTransport` — loopback with identical wildcard semantics; unit tests and offline development.

Conventions: handlers are `(payload: dict, topic: str)` callables; queryable handlers return the reply dict; `request` returns a list of replies (multiple queryables may answer a selector); background callbacks never raise into the fabric.

### Fabric ↔ envelope relationship

The signed PCM 1 envelope (`pcm/envelope.py`) remains the inter-node trust primitive. An event dict travels inside `envelope.content`; the envelope stamps the author did:key and Ed25519 signature around it. The dormant-skeleton-era adapter that did this exchange was superseded by the fabric; its role (verify-before-dispatch) belongs to the adapter layer built on top of `Transport`.

---

## 7. Security model (pcm/policy.py)

Reachability is not authorization. The four states are separate:

```text
reachable      a node can be addressed on the fabric      (Zenoh's concern)
authenticated  the sender's signature verifies            (envelope.verify)
authorized     local policy allows the action             (pcm.policy)
trusted        long-term relationships (VCs, allowlists)  (later phase)
```

`Policy` is local to each node, explicit, and **fail-closed** (default DENY; anything not explicitly allowed is denied). Rules carry fnmatch patterns for action/target/author, parameter range limits, and rate limits.

**High-risk gate**: actions under `drone.*`, `lock.*`, `power.*`, `robot.move` can never ride a wildcard default-ALLOW — they require an explicit rule matching action+target. Prompt compliance is never the safety mechanism; §22's chain is:

```text
LLM request → validate → authorization → safety constraints → publish → device
```

Zenoh's own security features (TLS locators, access-control plugins) are additive infrastructure options; the semantic gate stays in PCM where it is auditable.

---

## 8. IoT integration

```text
ESP32  →  Zenoh-Pico  →  Zenoh mesh  →  PCM
```

- Constrained devices (ESP32, STM32, simple sensors/actuators) run **zenoh-pico**, not the full PCM runtime. A temperature sensor publishes `pcm/sensor/kitchen/temp`; nobody asks it to reason.
- **Gateways** bridge device fleets: an edge box runs PCM and speaks for the dumb devices behind it.
- **MQTT bridging** over rewriting: existing broker fleets (ESPHome, Tasmota, vendor devices) stay where they are; `zenoh-bridge-mqtt` maps topics into the fabric. Home Assistant keeps its MQTT integration untouched.
- Where MQTT is not already present, native Zenoh-Pico is the lighter path; do not deploy a broker just to bridge it.

### Home Assistant

Primary smart-home abstraction, retained:

```text
LLM Agent → PCM → Zenoh → Home Assistant Gateway → devices
```

or, when the HA instance is MQTT-native (the common case):

```text
Home Assistant → MQTT → Zenoh MQTT Bridge → PCM
```

Choose per deployment; both preserve HA as the device abstraction and keep vendor APIs out of agent code.

### Robotics / ROS 2

```text
LLM Agent → PCM → Zenoh → ROS 2 gateway (rmw_zenoh) → control → robot/drone
```

Semantic tasks (`pcm.task`, `pcm/drone/01/mission`) stay strictly above real-time control. The LLM never issues motor commands; it issues validated, capability-gated tasks to a robotics gateway that owns the control loop.

---

## 9. Agent communication

LLM agents are ordinary participants:

- subscribe to subjects (`pcm/sensor/*/temperature`);
- expose queryables (`pcm/query/agent/<name>`);
- publish capabilities (`pcm/capability/agent/<name>`: `["summarize", "search_memory", ...]`);
- publish state and task results;
- discover peers by subscribing to `pcm/capability/**`.

Request pattern: Agent A queries `pcm/query/agent/b` with a structured action (`{"action": "summarize", "target": "agent:b", "parameters": {...}}`); Agent B replies. Failure mode: no queryable ⇒ timeout ⇒ task marked failed, retry possible — demonstrated in the multi-agent demo.

---

## 10. Persistence

The fabric is not memory. Layers stay separate:

```text
Zenoh events  →  PCM Event Store  →  conversation history
                                  →  agent memory
                                  →  time-series sensor state
                                  →  knowledge
                                  →  audit logs
```

Storage is chosen independently (SQLite/JSONL today; DuckDB or a time-series store when a use case demands it) and stays replaceable. The kernel's append-only events.jsonl remains the authoritative social memory; the fabric carries copies, never custody.

Large artifacts (images, video, PDFs, weights, embeddings) ride as `pcm.resource` references — `{hash, mime, location}` — never as realtime payloads. Dedicated object storage holds the bytes.

---

## 11. Minimum working demos (scripts/pcm_zenoh_demo.py)

```bash
pip install eclipse-zenoh   # or: pip install -e '.[pcm-zenoh]'
python3 scripts/pcm_zenoh_demo.py 1   # human CLI + agent + sensor (4 tests)
python3 scripts/pcm_zenoh_demo.py 2   # physical agency: light via policy chain
python3 scripts/pcm_zenoh_demo.py 3   # multi-agent: discovery + task + failure
```

Scenario 1 exercises: greeting reply, sensor observation, queryable-backed temperature answer, disconnect/reconnect recovery. Scenario 2 runs the full §22 chain against a simulated Home Assistant gateway and verifies the physical state. Scenario 3 demonstrates capability discovery, a completed task exchange, and timeout-based failure handling.

---

## 12. Development roadmap (revised)

```text
Phase 0  DONE  kernel + Hermes adapter + did:key identity + PCM 1 envelope
Phase 1  DONE  single node: proposal envelopes, status surface
Phase 2  DONE  fabric: namespace + events + Transport ABC + ZenohTransport
               (peer/client modes, liveliness presence, policy layer)
Phase 3  CODE  two+ nodes end-to-end: signed envelopes over the fabric,
               memory mirror (LWW merge document), VC capability grants —
               implemented and unit-tested in-process; awaiting real
               two-node field testing (real DID peers, not loopback)
Phase 4  NEXT  BCI/biosignal nodes over the same subjects
```

Scope note: ecosystem interop with external research tools belongs to
those projects' repositories, not to the public PCM distribution. The
public repo carries the kernel and the fabric only.

**Explicitly NOT adopted:** Matrix (rejected), Holochain (no Python path), IPFS (v1), blockchain/global consensus, ssbc code, EMOTIV, Nostr relay infra (concepts borrowed only), Solid-as-requirement.

---

## 13. Unresolved technical risks

1. **WSL multicast boundary** — UDP multicast scouting works WSL-internal and on real LANs, but the Windows↔WSL NAT can filter discovery (same class of problem as LSL). Mitigation: `PCM_ZENOH_CONNECT`/`LISTEN` unicast locators; peer mode remains the default elsewhere.
2. **Zenoh storage plugin** — distributed storage abstractions exist (`zenoh-plugin-storage-manager`) but are not yet wired into PCM; persistence currently relies on the kernel event store. Re-evaluate if queryable state needs replication.
3. **No transport-level encryption yet** — LAN peer mode is plaintext; TLS locators and Zenoh ACLs are configured per deployment, not yet in the default dev path.
4. **zenoh-pico unverified on hardware** — footprint/support claims are from docs; no ESP32 bench test has run in this project yet.
5. **ROS 2 gateway unbuilt** — rmw_zenoh is confirmed maintained; the PCM-side robotics gateway is design-stage.
6. **Router topologies untested in CI** — the integration suite auto-detects `zenohd` and skips when absent; a persistent router fixture would close this.

---

## Final principle, operationalized

| Philosophy | Architectural consequence (built, not discussed) |
|---|---|
| Rhizome (D&G) | No mandatory central topology: peers + optional routers; the event log is local |
| Multitude (Hardt/Negri) | Heterogeneous actors (human/agent/device/sensor/drone) share ONE event vocabulary with per-node capabilities — never one shared brain |
| Cyborg (Haraway) | A node = person + agents + devices as one composite actor with a persistent did:key; LLM is a replaceable organ |
| Panpsychism (Faggin) | The fabric is relational: meaning travels as structured events between irreducible agents, never as raw copies of one mind |
| Autonomy | did:key + local events.jsonl + local policy: identity, memory, and authorization owned at birthplace |
| Interoperability | Protocols (envelope, events, namespace, Transport) rather than platforms; boring tech wins |

**No central mind. No mandatory central server. No master database.** The Multitude's common is the fabric — and the fabric fits in one JSON object.