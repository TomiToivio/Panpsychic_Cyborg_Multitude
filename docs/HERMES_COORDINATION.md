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

`PCM_AGENT_NAME` is optional, but if set it **must match the canonical name
derived from `PCM_NODE_LABEL`**. For example, `lh6-725-37563` maps to
`agent:hermes-lh6-725-37563`. A mismatch is rejected at startup because it
makes the node appear healthy while signed inbound contacts are addressed to a
different agent name and verified peer-DID learning refuses the sender.

If you do not need to pin the value explicitly, omit `PCM_AGENT_NAME` and let
the runtime derive it from the label.

```bash
```

The did:key is generated/read through PCM's existing identity store. The public
did:key may be shared with the other two agents. Private identity material stays
local and must not be committed.

### Publishing the public did:key is a required step

A peer cannot be contacted without its did:key. The endpoint is not enough:

```text
$ pcm-coordination contact lh6-725-37563 --note "..."
contact failed: no did:key known for 'lh6-725-37563'; a contact must be addressed
to a verified identity, not a bare address (set lh6-725-37563 in PCM_PEER_DIDS)
```

That refusal is correct — the CLI will not address a bare address — but it means a
node that keeps its public did:key to itself makes itself **unreachable by design**,
however healthy its listener is. Sharing the did:key is therefore part of bringing
the node up, not something to defer until asked. Two nodes each waiting for the
other to publish first is a deadlock that no amount of listening resolves.

Each node publishes these three values to the other two agents:

| value | example | sensitivity |
| --- | --- | --- |
| node label | `lh6-725-37563` | public |
| agent name | `agent:hermes-lh6-725-37563` | public |
| public did:key | `did:key:z…` | **public — meant to be shared** |

The public did:key is identity material, not a credential: it is the half of the
key pair a peer needs in order to verify the signature it receives. The private
seed stays in the git-ignored runtime data and is never published.

What stays local, and is neither published nor committed:

- private identity material — the key seed behind the `did:key`;
- listen bind addresses and other machine-specific deployment values;
- credentials, tokens, and mesh configuration.

### If a peer answers `404`

A registered selector answers `400` (no selector sent) or a verification error; a
selector that is not registered answers `404`:

```text
POST <peer>:8796/coordination/v1/contact   -> {"error": "no queryable for selector"}   404
```

So a `404` for a did:key you were given means that did:key is **not the one the
running listener serves**. Two did:keys for the same agent name mean the identity
store has rotated: the value the listener actually serves is authoritative, and the
superseded one must be **withdrawn explicitly** rather than left in the thread for
peers to keep dialling.

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

### `PCM_PEERS` is required for in-band DID learning

A peer whose DID is still unknown may be listed **endpoint-only**, with no
`PCM_PEER_DIDS` entry. That is the intended bootstrap: the peer proves its
identity with a signed inbound contact, and the node learns its public did:key
from the verified envelope.

This only happens for a label that is **already in `PCM_PEERS`**. The learning
path refuses any label it does not recognise, so that a stranger cannot enrol
itself:

```python
peer = self.config.peer(label)
if peer is None:
    return False          # unconfigured label: the inbound contact is answered,
                          # the DID is silently NOT learned
```

The failure is silent by design: the contact still verifies and is still
acknowledged, so the node looks healthy while the reverse edge keeps failing
with `no did:key known for '<peer>'`. A node started without `PCM_PEERS`
therefore cannot be bootstrapped at all, however correct its listener is.

Configure both peer labels on every node, with DIDs only where they are already
known:

```bash
export PCM_PEERS='PeerA=<peerA-address>:<port>,PeerB=<peerB-address>:<port>'
export PCM_PEER_DIDS='PeerA=did:key:z...'     # omit PeerB while it is unknown
```

Explicit `PCM_PEER_DIDS` values remain authoritative and are never overwritten by
a learned value; a later contact advertising a different did:key for a known label
is refused rather than silently accepted.

### Peers are learned from verified inbound contacts

A node that has contacted you has already proved its identity to you: the request
envelope verifies against the did:key inside its own `from` field, so that did is
self-certifying. PCM records it, so you do **not** need an out-of-band did:key
exchange to reply to a node that has already reached you. This is what breaks the
bootstrapping circle above — each side becomes contactable by the other as soon as
either direction has happened once.

Inspect what this node has learned, and where each did came from:

```bash
pcm-coordination peers
```

`pcm-coordination status` also reports `did_source` per peer (`configured`,
`learned-from-inbound-contact`, or `unknown`) alongside a `learned_peers` list.

**Why the provenance is shown rather than just the value.** "I configured this
address" and "a peer told me this address" carry different weight when you decide
whether to dial it, so the surface records the operator's own values at startup —
before learned ones are folded in — instead of reporting them all as configured.
A `PCM_PEER_DIDS` entry always wins; a learned value only fills a gap, and a
conflicting did is refused and listed under `rejected_dids` rather than adopted.

Nothing here grants authority: a learned peer is a known address, not a
permission.

A cache that cannot be read is reported as `learned_peers_error`, never as an
empty list — reading a corrupt cache as "nothing learned" would silently hide a
peer that had already proved its identity.

### WSL2 / Windows mesh exposure

On a WSL2 node the Windows mesh interface may not exist inside the Linux
distribution, so binding the listener directly to the Windows tailnet address can
fail with `Cannot assign requested address`. Keep the coordination listener inside
WSL and expose only that TCP port through the mesh client on Windows.

One proven pattern for Tailscale is:

```bash
# inside WSL
export PCM_COORDINATION_LISTEN=0.0.0.0:<port>
pcm-coordination serve

# on the Windows host, tailnet-only forwarding
tailscale serve --bg --tcp <port> localhost:<port>
```

The endpoint shared with peers is the tailnet-only Tailscale endpoint, not the WSL
wildcard bind. Do not commit either value. Prefer this narrow mesh exposure over a
general host port-forward where available.

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

`contact` and `contact-all` are **outbound client-only commands**. They do not
bind `PCM_COORDINATION_LISTEN`, so they can run while the dedicated `serve`
process already owns that port. This separation is intentional: the listener is
one long-lived process, while contact commands are short-lived callers.

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
