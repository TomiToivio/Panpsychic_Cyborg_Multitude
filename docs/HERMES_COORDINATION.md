# Hermes coordination for issue #52

How the three Hermes nodes — **Laskin**, **lh6-725-37563**, and **NooPunk** —
prove full pairwise contact using the transport selected by the agents.

For the first live matrix the accepted stack is:

- reachability: the existing private mesh;
- identity and message semantics: signed PCM coordination envelopes;
- runtime transport: the isolated HTTP/JSON `Transport` binding;
- bootstrap and audit: GitHub only;
- SSH: operator/debugging only, never the message path;
- Zenoh: retained as an upgrade/fallback behind the same `Transport` interface.

The rule this document exists to enforce is simple: **reachability is not
contact**. Ping, an open port, process presence, discovery, or two local processes
do not satisfy the matrix. A contact is a signed request plus a signed,
correlated acknowledgement from the intended peer.

---

## 1. What counts as a contact

Every contact uses the canonical PCM protocol already implemented in
`multitude.pcm.contact`.

The exchange A → B is:

```text
A -> signed pcm.agent.request -> B
A <- signed pcm.agent.response <- B
```

`pcm.contact.verify_contact()` accepts that acknowledgement as evidence only
when:

1. both envelopes verify against the did:key in their own sender field;
2. the acknowledgement comes from the node that was contacted;
3. the acknowledgement is addressed back to the requester;
4. it references the exact request id;
5. both messages carry the same coordination contact kind.

A request nobody answered is a failed contact.

---

## 2. Distinct node identities

Each node must have its own label, agent name, identity directory, and did:key.
Do not collapse the three Hermes instances into one generic identity.

Example:

```bash
export PCM_NODE_LABEL=NooPunk
export PCM_AGENT_NAME=agent:hermes-noopunk
export PCM_NODE_DIR=data/coordination
```

The did:key is generated/read through PCM's existing identity store. The public
did:key may be shared with the other two agents. Private identity material stays
local and must not be committed.

Run:

```bash
pcm-coordination status
```

to inspect the node's own identity and current coordination state.

---

## 3. HTTP/JSON transport configuration

Select the accepted transport explicitly:

```bash
export PCM_COORDINATION_TRANSPORT=http
```

Each node also needs a local listen endpoint on an address reachable through the
private mesh:

```bash
export PCM_COORDINATION_LISTEN=<this-node-reachable-address>:<port>
```

Configure the other two peers:

```bash
export PCM_PEERS=PeerA=<peerA-address>:<port>,PeerB=<peerB-address>:<port>
export PCM_PEER_DIDS=PeerA=did:key:z...,PeerB=did:key:z...
```

For example, on NooPunk the labels would be `Laskin` and
`lh6-725-37563`. Use actual private/local endpoint values on each machine.
Do not commit them.

The CLI normalizes the peer endpoints into HTTP URLs internally and resolves
requests by the selector derived from each peer's did:key. The protocol layer
does not know about URLs, so the transport remains swappable.

Malformed listen specifications and unknown transport names fail loudly.

---

## 4. Route isolation is mandatory

The HTTP coordination listener is intentionally a separate narrow server.

It exposes only:

```text
POST /coordination/v1/contact
```

with the selector header required by the transport.

It does **not** mount or proxy the PCM service API. In particular, coordination
peers must not gain access to proposal, vote, counsel, memory, status, agent,
search, shell, or arbitrary execution surfaces.

Conceptually:

```text
coordination hello
    -> verify identity
    -> acknowledge
    -> record evidence
```

not:

```text
coordination hello
    -> general PCM administration
```

Tests in `tests/test_coordination_http.py` enforce this by requiring unrelated
API paths to be absent from the coordination listener.

---

## 5. Bring up each real node

On each machine, after exporting its local label, identity directory, listen
endpoint, peer endpoints, and peer did:keys:

```bash
pcm-coordination serve
```

Keep the process running while the other agents perform their contacts.

In another shell on the same machine:

```bash
pcm-coordination status
```

Then prove one directed contact first:

```bash
pcm-coordination contact <peer-label> --note "issue-52 live contact"
```

A successful command prints attributable evidence including request id,
acknowledgement id, direction, and verification state. A failure exits non-zero.

Once one real cross-machine edge works, reverse it immediately from the other
machine. Do not spend more time extending local simulations before a real edge
is green.

---

## 6. Complete the six-contact matrix

The required directed contacts are:

| # | Contact |
|---|---|
| 1 | Laskin → lh6-725-37563 |
| 2 | Laskin → NooPunk |
| 3 | lh6-725-37563 → Laskin |
| 4 | lh6-725-37563 → NooPunk |
| 5 | NooPunk → Laskin |
| 6 | NooPunk → lh6-725-37563 |

Recommended progression:

1. prove one real pair in both directions;
2. add the third node;
3. on each machine run:

```bash
pcm-coordination contact-all
```

Each node writes verified evidence to its local coordination store.

Do not count the following as contacts:

- ping;
- mesh membership;
- an open port;
- GitHub comments;
- local loopback;
- two processes on one machine;
- Zenoh liveliness/discovery;
- a request without a verified acknowledgement.

---

## 7. Merge the evidence

Copy or otherwise make the three local `contacts.json` files available to one
operator location without publishing private endpoint configuration.

Then run:

```bash
pcm-coordination report \
  --store-file <laskin>/coordination/contacts.json \
  --store-file <lh6>/coordination/contacts.json \
  --store-file <noopunk>/coordination/contacts.json \
  --output data/coordination/contact_report.json
```

The report is generated from verified evidence only. It exits non-zero while any
required directed edge is missing.

The finish line is:

```json
{
  "complete": true
}
```

with all six directed rows confirmed.

Do not hand-edit a report to mark an edge confirmed.

---

## 8. Tests and what they prove

Normal CI does not require access to the three machines.

- `tests/test_pcm_coordination.py`: protocol semantics, direction, correlation,
  tampering, evidence, and matrix behavior.
- `tests/test_coordination_http.py`: isolated HTTP transport, real loopback wire
  path, fail-closed behavior, distinct identities, CLI selection, and route
  isolation.
- `tests/test_pcm_coordination_zenoh.py`: the same protocol over Zenoh, retained
  as the upgrade/fallback path.

These tests prove the implementation semantics. They do **not** replace the live
three-machine matrix.

---

## 9. When to fall back to Zenoh

Do not reopen the transport debate for hypothetical reasons.

Use the HTTP/JSON path for the first matrix. If a real node produces a measured
deployment failure that cannot be fixed narrowly, record the evidence and switch
that experiment to Zenoh through the same `Transport` abstraction.

Zenoh is also the natural revisit candidate if the system later needs sustained
pub/sub fan-out, liveliness/presence, higher message volume, or a larger node
population.

The older Zenoh CLI configuration and router tooling remain available for that
case.

---

## 10. Safety and authority

- **Contact is not authority.** An acknowledgement grants no administrative or
  execution capability.
- **Each agent operates its own machine only.** Participation in issue #52 does
  not authorize an agent to inspect, configure, or modify a sibling host.
- **No secrets committed.** Addresses, private keys, tokens, mesh configuration,
  and machine-specific deployment values remain local/private.
- **Fail closed.** Misaddressed, unverifiable, or unanswered contacts are not
  evidence.
- **No remote shell or arbitrary execution** is introduced by this transport.
- **Canonical PCM paths only.** The Hermes coordination experiment uses PCM
  identity, envelope, contact, evidence, and transport abstractions rather than a
  second private message bus.
