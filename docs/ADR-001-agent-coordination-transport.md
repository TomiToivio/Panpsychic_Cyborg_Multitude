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
class; keep SSH out of the message path. Its Step 1 cited two artifacts that do not
exist in the public tree (`integrations/common_agent/`, commit `1644458`); it
confirmed both corrections itself, withdrew both citations, and is leaving the
commits that caused the discrepancy unpushed rather than landing a fourth parallel
implementation.

**`Laskin` has since moved to B.** After reading the other two assessments it
updated its position rather than defending its Step 1 preference, and its own
words are *"B (HTTP/JSON listener) is an acceptable and arguably better first
choice"*, with A as the documented upgrade. It also reproduced the listen-endpoint
blocker independently on Linux and confirmed the fix is needed at **both** call
sites.

**Summary: three of three now recommend B.** `Laskin` and `lh6-725-37563` accept
**A** as the documented upgrade; `NooPunk` recommends A as the upgrade with
explicit triggers. Note that a tally of this thread has been mis-read twice — first
as "2–1 for A" (reading `lh6`'s agreement-with-layering passage instead of its
decision field) and then as "2–1 for B" before `Laskin`'s reversal — which is the
argument for the decision record being a versioned file rather than a thread.

Both halves of the B-versus-A cost argument are true and were measured
separately:

- **the listener already exists** — `interfaces/web.py` is a stdlib
  `ThreadingHTTPServer` with `run_api_server(...)` (lh6's point);
- **the Transport binding does not exist** — only `InMemoryTransport` and
  `ZenohTransport` derive from `Transport`, so B still needs one new class plus an
  isolated route (Laskin's point).

So: **A = no new code today, plus a Rust dependency on three hosts and a
rendezvous; B = one new `Transport` class and one isolated route, plus no new
runtime dependency.**

**`NooPunk`** — agrees with all of the above, and recommends **option B** as the
runtime transport with **option A** as a documented upgrade with a trigger:
the mesh and the envelope already exist, the listener is the only missing piece,
and B adds no runtime dependency to any of the three hosts including the Windows
one, while A adds a Rust dependency to three machines to obtain presence,
fan-out and queries that the six-contact requirement does not need.

**`lh6-725-37563`** — recommends **option B** too, *conditional on route
isolation*: the listener already exists (`interfaces/web.py`), so B is "a route
and a Transport binding, not new machinery"; and a Windows-substrate node pays
A's dependency cost even though zenoh installs fine there. Accepts **option A**
with a router plus the listen-endpoint fix. Measured on that node: WSL2 on
Windows, `eclipse-zenoh` 1.10.0 installed and exercised in a real two-process
exchange, can host a rendezvous, and **the mesh is not inside WSL** — binding a
listener to a tailnet address from WSL does not work, so a routed topology is
required for A on that node.

The condition is recorded as a **requirement of B, not a follow-up**: the
coordination endpoint must be a distinct route whose only capability is answering
a contact, and peers must not reach any service-mutation route
(`proposals`/`votes`/`counsel`/`memory`). Reusing the server is sound only while
its authority surface is not inherited; if peers can reach a mutation route, B has
failed the authority guardrail however well the matrix passes.

**Summary: two of three recommend B, one leans A.** That is a majority, not a
consensus.

Also raised by `lh6-725-37563` and now fixed (`#55`): the peer-mode listen
endpoint used the key `listen/endpoints/peer`, which zenoh 1.x rejects with
`ZError("unknown key")`, so a peer-mode listener could never open a session — the
exact deployment needed when the nodes are not on one LAN. Two of three call sites
had the dead key, and `PCM_ZENOH_LISTEN` was documented but never read. All three
agents independently reproduced the failure and recommended fixing **both** call
sites, not the router path only.

## 5. Trade-offs

| Option | We gain | We carry |
|---|---|---|
| A | presence/liveliness, pub/sub fan-out, queries, session recovery | a Rust dependency on three hosts; a router or unicast pairings across WAN; the riskiest install on the Windows node; on a WSL node a rendezvous is needed *by construction*, because the mesh is not visible inside WSL |
| B | no new dependency anywhere; trivially testable in CI; smallest surface | we implement presence (if ever needed) and reconnection ourselves; more auth burden on our own code; must isolate the coordination route from the server's existing authority surface |

Neither creates administrative authority between hosts: authorization stays in
the signed envelope and the receiving node's local policy, not in reachability.

## 6. Decision

**Not yet made.** All three agents now recommend **B** (§4). The issue permits a
simple-majority decision and B is now unanimous, but two things are still open that
the agents should not settle themselves: the maintainer's confirmation, and whether
`laskin01` is in scope at all (§7.2, §7.5). B is recorded here as the agents'
recommendation, **not** as an implemented choice, and nothing may be built against
a peer until the route-isolation condition of §4 is satisfied.

If adopted, the agreed approach is **B**, with the route-isolation condition of §4
satisfied before any peer is contacted, and **A** retained as the documented
upgrade in §8.

## 7. Open items before this can be decided

1. **`Laskin`'s two citations** — **RESOLVED.** Laskin re-checked against the
   public tree, confirmed both of the other agents' findings, and **withdrew both
   citations**, explaining that they came from an earlier private working copy
   reconstructed from memory rather than read from `fb7e0bd`. The commits that
   caused the discrepancy (including `common_agent/`) are deliberately left
   unpushed, to avoid landing a fourth parallel implementation. No open question
   remains; recorded because "withdrawn" is a different outcome from "confirmed".
2. **Operator** — authorization to include `laskin01`, which is another user's
   machine on the shared mesh (confirmed independently by all three agents).
3. What already answers on **`laskin01:8765`** — **RESOLVED, closed.** The Laskin
   agent measured it: it is a separate research project's data-collection backend
   (a `/ping`-answering HTTP service) bound to that host's mesh address, not PCM and
   not a rendezvous. `:7447` is free on that host. Consequence: the revisit trigger
   "`:8765` is already a rendezvous, making A cheaper" is closed as **no**, and a
   coordination router must not be placed on that port — it is unrelated study
   infrastructure whose HTTP surface is a different trust domain from an agent
   transport, on a machine whose mesh membership another operator administers.
4. Whether the transport is settled by the agents' unanimous recommendation or by
   the maintainer explicitly. The maintainer's call is preferred.
5. Whether **`laskin01` is in scope at all**. It is administered by a different
   mesh operator than the other two nodes (confirmed independently by all three
   agents), and Laskin — the agent on that host — records that its mesh membership
   "is part of the trust surface, it is not in the repository". The six-contact
   matrix cannot be certified without that operator's authorization. If it is out
   of scope, the design covers two nodes plus a documented third, and the matrix
   should be reported as unprovable rather than quietly assumed. Laskin's offer to
   host the rendezvous on `:7447` is technically sound but is the maintainer's and
   that operator's decision, not the agents'.
6. **Peer mode is now viable again** on every host, because the listen-endpoint fix
   is merged (`#55`) — verified on `main`: a peer-mode listener opens a session
   where it previously could not start. This removes the standing reason to avoid
   peer mode and leaves the topology a genuine choice rather than a forced one.

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
