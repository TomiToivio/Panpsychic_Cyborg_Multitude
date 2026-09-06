# -*- coding: utf-8 -*-
"""Economy ValueFlows domain — the production of the Common (issue #11).

ValueFlows (https://valueflows.app) is the vocabulary this module speaks
for describing material and immaterial flows — needs, offers, work,
commitments, contributions, resources — **without reducing them to money,
private property, or corporate accounting**.

Design contracts (issue #11):

* **Optional domain layer, never governance.** ValueFlows describes
  *what flows*; PCM governance determines *what should happen and under
  which rules*. This module records flows; it never decides them.
* **One Multitude, many identifiable participants.** Humans, AI
  assemblages, organizations and other rhizomes stay individually
  identifiable as flow participants — the rhizome never becomes one
  corporate economic actor.
* **Commitment ≠ EconomicEvent.** A commitment is what was *promised*;
  an economic event is what *actually happened*. ValueFlows itself
  distinguishes planning from observation; so does this module, and the
  kernel's provenance discipline keeps them separate in the log.
* **Interoperable projection, simple internals.** Internally we keep
  PCM's Pydantic/event-sourced records (no RDF dependency); export to
  JSON-LD in the ValueFlows namespace (`https://w3id.org/valueflows/ont/vf#`)
  is a clean projection function, not the storage format.
* **The Common is not what exists before cooperation; it is continuously
  produced and reproduced through cooperation.** Every event here is a
  record of that production — including care, knowledge, maintenance and
  shared memory, not only commodities.

Event sourcing: all state changes are append-only kernel events
(`vf_*` types) owned by this module through the domain registry
(`multitude.domains`); the core reducer never grows ValueFlows branches.
"""
from __future__ import annotations

from typing import Any

from multitude.models import (
    AssemblageRecord,
    EconomicEventVFRecord,
    EconomicIntentRecord,
    EconomicCommitmentRecord,
    EconomicAgreementRecord,
    EconomicResourceVFRecord,
    ProcessVFRecord,
)

# Official ValueFlows ontology namespace.
VF_NAMESPACE = "https://w3id.org/valueflows/ont/vf#"

# Event vocabulary owned by this domain.
VF_EVENT_TYPES = frozenset({
    "vf_intent_created",
    "vf_agreement_created",
    "vf_commitment_created",
    "vf_economic_event_recorded",
    "vf_resource_created",
    "vf_process_created",
})

# Record kind -> ValueFlows class, for JSON-LD projection.
_VF_CLASS = {
    "intent": "Intent",
    "agreement": "Agreement",
    "commitment": "Commitment",
    "economic_event": "EconomicEvent",
    "resource": "EconomicResource",
    "process": "Process",
}


class VFError(Exception):
    """Invalid ValueFlows operation (unknown reference, malformed flow)."""


# ----------------------------------------------------------------- agents

def _vf_agent_ref(rhizome: Any, name_or_id: str) -> dict[str, Any]:
    """Resolve a flow participant to a VF Agent reference.

    Members, assemblages and registered economic agents all resolve;
    the resolved reference carries the PCM provenance kind so flows
    never collapse distinct participants into one actor.
    """
    member = rhizome.member_by_name(name_or_id)
    if member is not None:
        return {"@id": f"urn:pcm:member:{member.name}",
                "@type": "vf:Person" if member.kind.value == "biological"
                else "vf:Organization",
                "name": member.name, "pcm_kind": "member"}
    assemblages = getattr(rhizome, "assemblages", {})
    # assemblages are keyed by id; also accept a direct name match
    matches = [a for a in assemblages.values() if a.name == name_or_id]
    if matches:
        asm = matches[0]
        label = asm.name or name_or_id
        return {"@id": f"urn:pcm:assemblage:{label}", "@type": "vf:Organization",
                "name": label, "pcm_kind": "assemblage",
                "components": [
                    {"role": c.role,
                     "part": c.ref.id if c.ref else c.label, "kind": c.kind}
                    for c in asm.components
                ]}
    agents = getattr(rhizome, "economic_agents", {})
    if name_or_id in agents:
        agent = agents[name_or_id]
        return {"@id": f"urn:pcm:economic-agent:{agent.name}",
                "@type": "vf:Organization",
                "name": agent.name, "pcm_kind": "economic_agent"}
    raise VFError(f"no ValueFlows agent '{name_or_id}'")


# ------------------------------------------------------------------ state

def replay(rhizome: Any, type_: str, payload: dict[str, Any]) -> None:
    """Domain reducer: replay one vf_* event into rhizome state.

    Mirrors the kernel's record dicts; validated at write time, trusted
    at replay time (the kernel re-validates provenance before emit).
    """
    store = getattr(rhizome, "vf_store", None)
    if store is None:  # pragma: no cover - kernel wires vf_store at init
        raise VFError("rhizome has no vf_store; ValueFlows domain not mounted")
    if type_ == "vf_intent_created":
        rec = EconomicIntentRecord.model_validate(payload["intent"])
        store["intents"][rec.id] = rec
    elif type_ == "vf_agreement_created":
        rec = EconomicAgreementRecord.model_validate(payload["agreement"])
        store["agreements"][rec.id] = rec
    elif type_ == "vf_commitment_created":
        rec = EconomicCommitmentRecord.model_validate(payload["commitment"])
        store["commitments"][rec.id] = rec
    elif type_ == "vf_economic_event_recorded":
        rec = EconomicEventVFRecord.model_validate(payload["economic_event"])
        store["economic_events"][rec.id] = rec
    elif type_ == "vf_resource_created":
        rec = EconomicResourceVFRecord.model_validate(payload["economic_resource"])
        store["resources"][rec.id] = rec
    elif type_ == "vf_process_created":
        rec = ProcessVFRecord.model_validate(payload["process"])
        store["processes"][rec.id] = rec
    else:  # pragma: no cover - registry guarantees the vocabulary
        raise VFError(f"unknown ValueFlows event type '{type_}'")


# --------------------------------------------------------------- JSON-LD

def to_jsonld(rhizome: Any, record_kind: str, record_id: str) -> dict[str, Any]:
    """Project one stored record to ValueFlows JSON-LD.

    Clean interoperability projection — PCM's internal model stays
    simple; the VF namespace mapping happens only at the boundary.
    """
    store = getattr(rhizome, "vf_store", None)
    if store is None:
        raise VFError("ValueFlows domain not mounted")
    bins = {
        "intent": store["intents"], "agreement": store["agreements"],
        "commitment": store["commitments"],
        "economic_event": store["economic_events"],
        "resource": store["resources"], "process": store["processes"],
    }
    if record_kind not in bins:
        raise VFError(f"unknown record kind '{record_kind}' - valid: {sorted(bins)}")
    record = bins[record_kind].get(record_id)
    if record is None:
        raise VFError(f"no {record_kind} '{record_id}'")
    vf_class = _VF_CLASS[record_kind]
    data: dict[str, Any] = {
        "@context": {
            "vf": VF_NAMESPACE,
            "pcm": "https://github.com/TomiToivio/Panpsychic_Cyborg_Multitude#",
        },
        "@type": f"vf:{vf_class}",
        "@id": f"{VF_NAMESPACE}{vf_class}/{record_id}",
    }
    plain = record.model_dump()
    # provenance fields project to VF agent properties; PCM identity kept.
    agent_fields = {
        "created_by": "creator", "committed_by": "committedBy",
        "owed_by": "provider", "owed_to": "receiver",
        "provider": "provider", "receiver": "receiver",
        "recorded_by": "recordedIn", "custodian": "custodianOf",
    }
    for field, vf_prop in agent_fields.items():
        if field in plain and plain[field]:
            try:
                data[f"vf:{vf_prop}"] = _vf_agent_ref(rhizome, str(plain[field]))
            except VFError:
                data[f"vf:{vf_prop}"] = str(plain[field])  # external agent
    # everything else projects as a VF-namespaced literal
    skip = set(agent_fields) | {"id", "meta"}
    vf_prop_names = {
        "title": "name", "description": "note", "ts": "created",
        "due_ts": "hasCommitmentDate", "quantity": "resourceQuantity",
        "unit": "unit", "kind": "intentType", "status": "progressState",
        "action": "action", "process_id": "inputOf",
        "input_resource_ids": "inputOf", "output_resource_ids": "outputOf",
        "agreement_id": "realizationOf", "commitment_id": "realizationOf",
        "commitment_ids": "realizationOf", "resource_ids": "involves",
        "parties": "participant", "name": "name",
    }
    for key, value in plain.items():
        if key in skip or value in (None, [], "", {}):
            continue
        data[f"vf:{vf_prop_names.get(key, key)}"] = value
    # PCM provenance rides in its own namespace, never erased.
    data["pcm:internalId"] = record_id
    data["pcm:meta"] = plain.get("meta", {})
    return data


__all__ = [
    "VF_NAMESPACE",
    "VF_EVENT_TYPES",
    "VFError",
    "replay",
    "to_jsonld",
    "_vf_agent_ref",
]