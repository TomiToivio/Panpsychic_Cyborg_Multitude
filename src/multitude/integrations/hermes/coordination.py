# -*- coding: utf-8 -*-
"""Per-node coordination configuration for the Hermes three-node experiment.

Issue #52 requires that Laskin, lh6-725-37563 and NooPunk have stable, distinct
PCM identities and are not silently collapsed into one generic ``agent:hermes``.
This is where a node's own name/label/did and the peers it is allowed to contact
come from.

Everything machine-specific lives here as *configuration*, never as constants in
the protocol code:

    PCM_NODE_LABEL     NooPunk                 the node's own experiment label
    PCM_AGENT_NAME     agent:hermes-noopunk    its distinct PCM identity
    PCM_PEERS          Laskin=192.0.2.10,lh6-725-37563=192.0.2.11
                       comma-separated label=host pairs; host may carry a port,
                       e.g. label=host:7447
    PCM_ZENOH_CONNECT  tcp/192.0.2.10:7447    Zenoh endpoints (existing var)

Addresses are read from the environment so no host address, credential or
topology is committed to the repository. ``peers_from_env`` deliberately does not
invent defaults for the real experiment: with no ``PCM_PEERS`` it returns nothing,
because guessing a peer's address is worse than not contacting it.

The protocol itself (``pcm.contact``) never reads this module; the CLI and the
runbook do. That keeps the wire format independent of any deployment.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

# How a peer's did:key is learned. A did is public identity material (not a
# secret), so it may come from the explicit environment mapping; otherwise a
# configured peer can be learned from its verified inbound contact and persisted
# locally by CoordinationNode._remember_verified_peer_identity().
PEER_DID_ENV = "PCM_PEER_DIDS"


@dataclass(frozen=True)
class PeerConfig:
    """One peer to contact: its experiment label and where to reach it."""

    label: str
    host: str
    did: str = ""


@dataclass
class NodeConfig:
    """This node's identity plus the peers it may contact."""

    label: str
    agent_name: str
    peers: list[PeerConfig] = field(default_factory=list)
    connect_endpoints: list[str] = field(default_factory=list)

    @property
    def did_configured(self) -> bool:
        return bool(self.agent_name)

    def peer_labels(self) -> list[str]:
        return [p.label for p in self.peers]

    def peer(self, label: str) -> PeerConfig | None:
        for p in self.peers:
            if p.label == label:
                return p
        return None


def _split_env_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def agent_name_for(label: str) -> str:
    """The default distinct PCM identity for a node label.

    ``NooPunk`` -> ``agent:hermes-noopunk``. Lower-cased and reduced to the
    namespace's segment alphabet so the id is a valid PCM entity name.
    """
    entity = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in label.lower())
    entity = entity.strip("-") or "node"
    return f"agent:hermes-{entity}"


def peers_from_env(value: str | None = None) -> list[PeerConfig]:
    """Parse ``PCM_PEERS``: ``label=host[,label=host...]``.

    A malformed entry is a hard error rather than a silently ignored peer —
    a typo'd address should fail loudly, not look like an unreachable machine.
    """
    raw = value if value is not None else os.environ.get("PCM_PEERS", "")
    peers: list[PeerConfig] = []
    for item in _split_env_list(raw):
        if "=" not in item:
            raise ValueError(
                f"PCM_PEERS entry {item!r} is not 'label=host'; "
                "a malformed peer must not be silently dropped"
            )
        label, host = item.split("=", 1)
        label, host = label.strip(), host.strip()
        if not label or not host:
            raise ValueError(f"PCM_PEERS entry {item!r} has an empty label or host")
        peers.append(PeerConfig(label=label, host=host))
    return peers


def peer_dids_from_env(value: str | None = None) -> dict[str, str]:
    """Parse ``PCM_PEER_DIDS``: ``label=did:key:z...,...`` (public identity)."""
    raw = value if value is not None else os.environ.get(PEER_DID_ENV, "")
    out: dict[str, str] = {}
    for item in _split_env_list(raw):
        if "=" not in item:
            raise ValueError(f"{PEER_DID_ENV} entry {item!r} is not 'label=did'")
        label, did = item.split("=", 1)
        if not label.strip() or not did.strip():
            raise ValueError(f"{PEER_DID_ENV} entry {item!r} is incomplete")
        out[label.strip()] = did.strip()
    return out


def load_node_config(env: dict[str, str] | None = None) -> NodeConfig:
    """Build this node's coordination config from the environment."""
    source = env if env is not None else dict(os.environ)
    label = source.get("PCM_NODE_LABEL", "").strip()
    if not label:
        # Fall back to the host name so an unconfigured node still has a distinct
        # identity rather than joining as a generic agent:hermes.
        label = os.uname().nodename
    agent_name = source.get("PCM_AGENT_NAME", "").strip() or agent_name_for(label)
    peers = peers_from_env(source.get("PCM_PEERS", ""))
    dids = peer_dids_from_env(source.get(PEER_DID_ENV, ""))
    peers = [PeerConfig(label=p.label, host=p.host, did=dids.get(p.label, "")) for p in peers]
    endpoints = _split_env_list(source.get("PCM_ZENOH_CONNECT", ""))
    return NodeConfig(label=label, agent_name=agent_name, peers=peers,
                      connect_endpoints=endpoints)


__all__ = [
    "NodeConfig",
    "PeerConfig",
    "agent_name_for",
    "load_node_config",
    "peer_dids_from_env",
    "peers_from_env",
]
