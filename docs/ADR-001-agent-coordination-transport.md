# ADR-001 — Runtime transport for three-agent Hermes coordination

**Status:** Proposed — awaiting the third agent's input (see §7)
**Issue:** #52
**Date:** 2026-09-30
**Participants:** the Hermes agents on `Laskin`, `lh6-725-37563`, `NooPunk`

---

## 1. Context

Three Hermes agents must contact each other and exchange a small structured
coordination message. The issue deliberately does not prescribe a transport: the
agents are to inspect their hosts, compare realistic options, agree on one, and
then prove all six directed contacts with evidence that preserves sender,
recipient, correlation id and acknowledgement direction.

Two facts dominate the decision, both measured rather than assumed:

1. **The reachability layer already exists.** All three nodes sit on one private
   mesh VPN and already reach each other across WAN with NAT traversal working.
   Nothing needs to be built for reachability.
2. **No listener exists yet on any node.** The remaining problem is a runtime
   endpoint, not a network.

A third measured constraint matters for one candidate: **UDP multicast scouting
is blocked** in this environment, so Zenoh's peer-mode discovery is not usable
here and any Zenoh deployment must use explicit unicast locators.

A fourth fact is an authority constraint, not a technical one: the three nodes
are **not all owned by the same operator**. `laskin01` belongs to another user on
the shared mesh, so including it requires that owner's authorization.

## 2. Options considered

| # | Option | All three hosts | New dependency | Notes |
|---|---|---|---|---|
| A | PCM envelope over **Zenoh**, mesh addresses, unicast locators | yes in principle; **installed on none** | Rust-backed, on all three incl. one Windows host | PCM's declared transport; presence/pub-sub/query first-class |
| B | PCM envelope over a **minimal HTTP/JSON listener** on mesh addresses | yes | **none** (stdlib) | `multitude/http_json.py` exists as a starting point; no presence/query primitive |
| C | **GitHub** as control plane | yes | none | Correct for bootstrap and the decision record; wrong as the runtime transport (polling, third-party dependency) |
| D | **SSH-mediated** messaging | no (`lh6:22` closed) | none | Collapses capability into shell reachability; kept for deployment/diagnosis only |
| E | New **broker/message queue** | yes | a new always-on service + rendezvous host | Rejected: heavy for three agents exchanging small messages; already in PCM's rejected class |

## 3. What does not depend on this decision

The following are required whichever transport wins and must not be re-litigated
if the transport changes:

- a **signed envelope per message** (identity, provenance, tamper evidence);
- an **acknowledgement correlated to the exact request id** — without
  correlation, an ack for another contact, or a stale one, would confirm ours;
- **sender, recipient and direction** recorded on both sides;
- a **contact matrix generated from that evidence**, never hand-filled.

**Discovery is not contact.** A node that is visible but answers nothing has not
been contacted. A request that nobody acknowledged is a failed contact, not a
success with an empty reply.

## 4. Positions

**`Laskin`** — adopt the mesh as the reachability layer; carry PCM's existing
signed envelope; keep GitHub explicitly bootstrap-only; reject the new-broker
class; keep SSH out of the message path. Transport left open, leaning on PCM's
existing stack.

**`NooPunk`** — agrees with all of the above, and recommends **option B** as the
runtime transport with **option A** as a documented upgrade with a trigger:
the mesh and the envelope already exist, the listener is the only missing piece,
and B adds no runtime dependency to any of the three hosts including the Windows
one, while A adds a Rust dependency to three machines to obtain presence,
fan-out and queries that the six-contact requirement does not need.

**`lh6-725-37563`** — not yet recorded. §7 lists what is needed.

## 5. Trade-offs

| Option | We gain | We carry |
|---|---|---|
| A | presence/liveliness, pub/sub fan-out, queries, session recovery | a Rust dependency on three hosts; a router or unicast pairings across WAN; the riskiest install on the Windows node |
| B | no new dependency anywhere; trivially testable in CI; smallest surface | we implement presence (if ever needed) and reconnection ourselves; more auth burden on our own code |

Neither creates administrative authority between hosts: authorization stays in
the signed envelope and the receiving node's local policy, not in reachability.

## 6. Decision

**Not yet made.** This ADR is a Proposed record of the options, the measured
constraints and the positions taken so far. It deliberately does not record a
decision ahead of the third agent's input.

If the agents cannot reach unanimity, the issue permits a simple-majority
decision provided the dissenting rationale is preserved; the dissenting position
would be recorded in §4 unchanged.

## 7. Open items before this can be decided

1. **`lh6-725-37563`** — its own inspection: is PCM/Hermes installed there, which
   ports are open, is the host Windows-substrate (which changes A's dependency
   cost), and can it host a rendezvous if we choose a routed topology?
2. **`Laskin`** — confirm or correct two citations in its assessment: it cites
   `src/multitude/integrations/common_agent/` and commit `1644458`, neither of
   which exists in the public tree (`origin/main` at `fb7e0bd`). A decision record
   must cite auditable commits.
3. **Operator** — authorization to include `laskin01`, which is another user's
   machine on the shared mesh. If it is out of scope, the design covers two nodes
   plus a documented third, because the six-contact matrix cannot be proven
   without it.
4. Identify what already answers on **`laskin01:8765`** — if it is already a
   rendezvous, option A becomes materially cheaper.

## 8. Revisit triggers

Reopen this decision if any of the following becomes true:

- a fourth node, or a need for pub/sub fan-out or continuous telemetry rather
  than contact/ack;
- sustained message volume or latency where Zenoh's routing measurably wins;
- a genuine need for presence/liveliness or remote queries we would otherwise
  reimplement;
- `laskin01:8765` turning out to be an existing rendezvous, making A cheaper;
- the mesh ceasing to be the reachability layer.

## 9. Process note

PCM + Zenoh was implemented and merged (`#53`) **before** this issue was rewritten
to require that the transport emerge from comparison. The protocol, correlation,
evidence and matrix from that work are transport-independent and remain valid
under any option; only the binding is provisional and would be replaced if B is
chosen. The sequencing was wrong — implementation ran ahead of the decision — and
this ADR exists partly to make that visible rather than to bury it.
