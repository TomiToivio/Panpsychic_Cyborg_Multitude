# Hermes coordination over PCM Zenoh (issue #52)

How three Hermes nodes — **Laskin**, **lh6-725-37563**, **NooPunk** — contact each
other through PCM over Zenoh, and how the six directed contacts are *proven*
rather than assumed.

The rule the whole document exists to enforce: **discovery is not contact.** A
liveliness token or a wildcard scan says a node exists. It does not say the node
received anything, agreed it was addressed, or answered. A contact here is a
signed request **and** a signed, correlated acknowledgement. "All three nodes
were visible" is not the matrix.

---

## 1. What a contact is, on the wire

Every contact uses the pieces the stack already has. No new bus, no new event
vocabulary:

| Piece | Used as |
|---|---|
| `pcm.envelope.Envelope` | both the request and the ack are signed, verifiable envelopes |
| `pcm.events.PcmEvent` (`pcm.agent.request` / `pcm.agent.response`) | the semantic body carried in `envelope.content.event` |
| `pcm/query/agent/<did-suffix>` | the request/response endpoint the contacted node answers on |
| `multitude.pcm.transport.Transport` | the seam: `HttpJsonTransport` in the selected deployment, `ZenohTransport` as the documented upgrade, `InMemoryTransport` in tests |

The transport is a swappable binding, not part of the protocol. ADR-001 records the
decision: the agents chose **HTTP/JSON** as the first runtime transport, over the
already-working private mesh, with Zenoh retained behind the same `Transport`
interface. Nothing below changes if the transport changes.

The exchange, A → B:

```
A --pcm.agent.request, signed by A's did:key--> B     (selector: B's pcm/query/agent/<suffix>)
A <--pcm.agent.response, signed by B's did:key-- B    (addressed to A, references A's request id)
```

The ack is evidence only when **all five** hold, and `pcm.contact.verify_contact`
checks each one rather than assuming it:

1. both envelopes verify against the did:key inside their own `from`;
2. the ack's `from` is the node that was contacted;
3. the ack's `to` is the node that made the request;
4. the ack references the exact request id (so an ack for somebody else's
   contact cannot confirm ours);
5. both carry the same contact kind (`coordination.hello`).

The selector is derived from the **did**, not from a configured name, so the
contacting and answering sides cannot drift apart about what to call each other.
The did is the identity that is already cryptographically verified.

---

## 2. Distinct identities

The three nodes must not collapse into one `agent:hermes`. Each node sets its own:

```bash
export PCM_NODE_LABEL=NooPunk
export PCM_AGENT_NAME=agent:hermes-noopunk     # default: agent:hermes-<label>, lower-cased
```

With no configuration a node still gets a distinct identity from its host name —
never the generic one. Its did:key comes from the same PCM identity store every
other PCM node uses (`pcm.bootstrap.ensure_node_identity` over the node
directory); this work adds no second identity store and no new key handling.

---

## 3. Configuration (nothing machine-specific is committed)

All of it is environment or runtime data under `data/`:

```bash
export PCM_COORDINATION_TRANSPORT=http        # http (selected) | zenoh (upgrade)
export PCM_COORDINATION_LISTEN=<mesh-addr>:8795   # where this node answers (http)
export PCM_NODE_LABEL=NooPunk
export PCM_AGENT_NAME=agent:hermes-noopunk
export PCM_PEERS=Laskin=<hostA>,lh6-725-37563=<hostB>
export PCM_PEER_DIDS=Laskin=did:key:z...,lh6-725-37563=did:key:z...
export PCM_NODE_DIR=data/coordination             # identity + evidence (runtime data)
```

- `PCM_COORDINATION_TRANSPORT` — which binding runs. `http` is the selected
  transport (ADR-001); `zenoh` is the documented upgrade. Defaulting behaviour: set
  `http` explicitly, or set only `PCM_COORDINATION_LISTEN` and it is inferred;
  unset with no listen address keeps the pre-existing Zenoh wiring, so an
  unchanged deployment does not change behaviour.
- `PCM_COORDINATION_LISTEN` — `<host>:<port>` this node binds. Use the mesh
  address so peers can actually reach it. A malformed value **fails loudly**
  rather than binding nothing and looking healthy.
- `PCM_PEERS` — `label=host` pairs. A malformed entry fails loudly; it is never
  silently dropped, because a typo'd address would then look like an unreachable
  machine. Under the `http` transport the host may be given with or without the
  scheme; it is normalised to a full URL.
- `PCM_PEER_DIDS` — the peers' **public** did:keys. A did:key is identity, not a
  credential: it contains no secret. Without it a contact is refused, because a
  contact must be addressed to a verified identity, not a bare address.

No address, token, key or topology is committed. The only public configuration is
the shape of these variables.

---

## 4. Topology

**Selected: HTTP/JSON over the private mesh (no discovery).** There is no
rendezvous and no router. Each node binds its own mesh address and is given the
peers' URLs, because reachability comes from the mesh and addressing is deployment
state rather than something the protocol discovers.

```bash
PCM_COORDINATION_TRANSPORT=http \
PCM_COORDINATION_LISTEN=<this-node-mesh-addr>:8795 \
PCM_NODE_LABEL=NooPunk PCM_AGENT_NAME=agent:hermes-noopunk \
PCM_NODE_DIR=data/coordination \
PCM_PEERS='Laskin=<laskin-mesh-addr>:8795,lh6-725-37563=<lh6-mesh-addr>:8795' \
PCM_PEER_DIDS='Laskin=did:key:z...,lh6-725-37563=did:key:z...' \
pcm-coordination serve
```

This binding deliberately has **no discovery**: no multicast, no scouting, no
service registry. A peer whose address you do not hold is a peer you cannot
contact, which keeps the exposed surface to exactly one route on one port and
makes the addressing explicit rather than ambient.

**Upgrade path: Zenoh.** Retained behind the same `Transport` interface and
selected with `PCM_COORDINATION_TRANSPORT=zenoh`; the pre-existing topology
instructions are kept below because the upgrade should be a configuration change,
not a rewrite. Two modes:

*Same LAN — peer mode.* Nodes find each other by UDP multicast scouting. No
server. (Note: multicast scouting is blocked in some environments, including at
least one of the three experiment nodes — explicit unicast locators are the safe
default there.)

```bash
PCM_COORDINATION_TRANSPORT=zenoh PCM_ZENOH_ENABLED=true PCM_NODE_LABEL=NooPunk \
PCM_PEERS=Laskin=192.0.2.10,lh6-725-37563=192.0.2.11 \
pcm-coordination serve
```

*Not on one LAN — routed mode.* One node (or a box) runs a Zenoh router; the
others are clients. This is the topology to use when the machines sit behind NAT
or on different networks.

Start a rendezvous router:

```bash
pcm-coordination-router --listen tcp/<reachable-address>:7447
```

`<reachable-address>` must be an address the other nodes can actually reach —
a tailnet address works well, since each machine keeps a stable one. Then each
node connects as a client:

```bash
PCM_COORDINATION_TRANSPORT=zenoh PCM_ZENOH_ENABLED=true PCM_NODE_LABEL=Laskin \
PCM_ZENOH_CONNECT=tcp/<reachable-address>:7447 \
PCM_PEERS=NooPunk=<addrNooPunk>,lh6-725-37563=<addrLh6> \
pcm-coordination serve
```

A router is **plumbing, never an authority**: it forwards, it does not authorize,
and the signed envelopes are what make a contact trustworthy.

---

## 5. Running it

Run one node interactively to watch it answer contacts:

```bash
pcm-coordination serve
```

Under the selected HTTP transport, `serve` binds `PCM_COORDINATION_LISTEN` and
answers on the single route `POST /coordination/v1/contact`. It fails closed: a
contact that is unverifiable, misaddressed, or sent to an unknown selector gets
silence (`404`), never an ack and never an error detail. Start it the same way on
each of the three nodes, each with its own label, identity and listen address.

Inspect what this node is and what is still missing:

```bash
pcm-coordination status
```

Contact one peer, or all configured peers:

```bash
pcm-coordination contact Laskin --note "hello from NooPunk"
pcm-coordination contact-all
```

`contact` prints the proven evidence (request id, ack id, timestamp) and exits
non-zero on failure. `contact-all` contacts every peer and reports each one
separately, so one unreachable machine does not hide the state of the others.

A contact succeeds only when the peer answers with a **correlated signed ack**. A
request nobody answered is a failure, not a success with an empty reply; a live
listener that has declared no queryable is *reachable and not contactable*, which
is the distinction the whole design rests on.

### The contact report

```bash
pcm-coordination report --store-file <nodeA>/coordination/contacts.json \
                        --store-file <nodeB>/coordination/contacts.json \
                        --output data/coordination/contact_report.json
```

The report is generated **only from verified evidence**. There is no command that
writes "confirmed" into a cell; `ContactMatrix.record()` refuses anything
unverified or off-list, and re-contacting a peer does not add a second row. The
report exits non-zero while any directed contact is missing, so it can gate a
procedure.

A two-node experiment does **not** produce a complete report, and that is the
point: two proven contacts out of six is `"complete": false` with four entries
under `"missing"`.

---

## 6. Verifying the full matrix

The six directed contacts, and what each requires:

| # | Contact | Requires |
|---|---|---|
| 1 | Laskin → lh6-725-37563 | Laskin configured with lh6's host + did |
| 2 | Laskin → NooPunk | Laskin configured with NooPunk's host + did |
| 3 | lh6-725-37563 → Laskin | lh6 configured with Laskin's host + did |
| 4 | lh6-725-37563 → NooPunk | lh6 configured with NooPunk's host + did |
| 5 | NooPunk → Laskin | NooPunk configured with Laskin's host + did |
| 6 | NooPunk → lh6-725-37563 | NooPunk configured with lh6's host + did |

Procedure:

1. on each of the three machines, export its own label and did, then
   `pcm-coordination serve`;
2. collect the three did:keys (from `status`, which prints the node's own did);
3. on each machine, set `PCM_PEERS` (the other two hosts) and `PCM_PEER_DIDS`
   (the other two did:keys);
4. on each machine run `pcm-coordination contact-all`;
5. merge the three `contacts.json` files with `pcm-coordination report` and check
   `"complete": true` with all six rows `"confirmed"`.

Each machine contributes its own half; the merge is what yields the whole matrix
(two nodes holding the same directed contact is one contact, not two).

---

## 7. What the tests cover, and what they cannot

| File | Requires | Covers |
|---|---|---|
| `tests/test_pcm_coordination.py` | nothing (in-process) | protocol semantics: correlation, direction, tampering, the matrix, fail-closed answering |
| `tests/test_pcm_coordination_zenoh.py` | `eclipse-zenoh` | the same protocol over **real Zenoh sessions**, and through a **router rendezvous** |

Normal CI is deterministic and needs no network: the in-memory tests always run,
and the Zenoh tests skip when the optional runtime is absent. The real matrix
across three hosts is a **procedure** (section 6), deliberately not a CI job.

---

## 8. Safety and boundaries

- **Contact is not authority.** Answering a contact performs no action for the
  requester and grants it nothing. `CoordinationNode.acknowledge` records and
  replies; it does not execute. An ack is not a capability.
- **No secrets committed.** Addresses, dids and endpoints are environment-only;
  identity material stays in the node's runtime directory under `data/`.
- **Fail closed.** An unverifiable or misaddressed contact is not answered and
  not recorded. A request nobody answered is a failed contact, not a success.
- **No remote execution.** The coordination surface can send and verify small
  JSON messages. There is no shell, no arbitrary code execution, and no implicit
  authority over another node.
- **Canonical paths only.** Everything rides the PCM envelope/event/transport
  layers. There is no second Hermes message bus.
