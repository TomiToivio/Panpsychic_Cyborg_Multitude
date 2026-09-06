# -*- coding: utf-8 -*-
"""Domain models for the Panpsychic Cyborg Multitude rhizome kernel.

Every participant in a rhizome is a node. Nodes are biological (humans,
acting through the interface) or technological (LLM-backed agents acting
through the same interface). Node equality is structural here, not
policy: both kinds speak, propose, vote, and remember through the same
APIs, and both are stored in the same append-only event log.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


def now_iso() -> str:
    """UTC timestamp, second precision, ISO 8601."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    """Readable unique id: prefix-YYYYMMDDHHMMSS-hex6."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:6]}"


class NodeKind(str, Enum):
    BIOLOGICAL = "biological"
    TECHNOLOGICAL = "technological"


class Layer(str, Enum):
    """The six layers of a human-like agent (whitepaper, section 4)."""

    PHYSICAL = "physical"
    BIOLOGICAL = "biological"
    SOCIAL = "social"
    LINGUISTIC = "linguistic"
    PSYCHIC = "psychic"
    CYBERNETIC = "cybernetic"


class PhysicalLayer(BaseModel):
    location_label: Optional[str] = None
    gps: Optional[dict[str, float]] = None
    environment: Optional[str] = None
    notes: str = ""


class BiologicalLayer(BaseModel):
    is_biological: bool = False
    species: Optional[str] = None
    sleep_state: Optional[str] = None
    hunger_state: Optional[str] = None
    mood: Optional[str] = None
    needs: list[str] = Field(default_factory=list)
    notes: str = ""


class SocialLayer(BaseModel):
    tribe_role: Optional[str] = None
    close_ties: list[str] = Field(default_factory=list)
    wider_networks: list[str] = Field(default_factory=list)
    systems: list[str] = Field(default_factory=list)
    notes: str = ""


class LinguisticLayer(BaseModel):
    languages: list[str] = Field(default_factory=list)
    vocabularies: list[str] = Field(default_factory=list)
    preferred_language: Optional[str] = None
    notes: str = ""


class PsychicLayer(BaseModel):
    is_conscious: Optional[bool] = None
    state: Optional[str] = None
    valence: Optional[str] = None
    attention: Optional[str] = None
    notes: str = ""


class CyberneticLayer(BaseModel):
    interface_mode: Optional[str] = None
    network_links: list[str] = Field(default_factory=list)
    devices: list[str] = Field(default_factory=list)
    model_runtime: Optional[str] = None
    notes: str = ""


class AgentProfile(BaseModel):
    physical: PhysicalLayer = Field(default_factory=PhysicalLayer)
    biological: BiologicalLayer = Field(default_factory=BiologicalLayer)
    social: SocialLayer = Field(default_factory=SocialLayer)
    linguistic: LinguisticLayer = Field(default_factory=LinguisticLayer)
    psychic: PsychicLayer = Field(default_factory=PsychicLayer)
    cybernetic: CyberneticLayer = Field(default_factory=CyberneticLayer)


class Position(str, Enum):
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"
    BLOCK = "block"


class Rule(str, Enum):
    CONSENSUS = "consensus"
    MAJORITY = "majority"
    UNANIMITY = "unanimity"


class ProposalStatus(str, Enum):
    OPEN = "open"
    ADOPTED = "adopted"
    REJECTED = "rejected"
    FAILED_QUORUM = "failed_quorum"


class Outcome(str, Enum):
    ADOPTED = "adopted"
    REJECTED = "rejected"
    FAILED_QUORUM = "failed_quorum"
    BLOCKED = "blocked"


class Member(BaseModel):
    id: str
    name: str
    kind: NodeKind
    voting: bool = True
    persona: Optional[str] = None
    model: Optional[str] = None
    joined_ts: str = ""
    profile: AgentProfile = Field(default_factory=AgentProfile)
    layers: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


class LexiconEntry(BaseModel):
    term: str
    definition: str
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    added_by: str = ""
    ts: str = ""


class DeviceRecord(BaseModel):
    id: str
    name: str
    kind: str
    owner: str = ""
    linked_member_id: Optional[str] = None
    status: str = "active"
    interface_modes: list[str] = Field(default_factory=list)
    location_label: Optional[str] = None
    gps: Optional[dict[str, float]] = None
    notes: str = ""
    sensitivity: str = "shared"  # shared | limited | private
    consent_required: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)
    registered_ts: str = ""


class BiometricSignalRecord(BaseModel):
    id: str
    ts: str
    member_id: str
    member_name: str
    signal_type: str
    value: Any
    unit: str = ""
    source: str = "manual"
    sensitivity: str = "private"  # shared | limited | private
    consent_required: bool = True
    meta: dict[str, Any] = Field(default_factory=dict)


class ResourceRecord(BaseModel):
    id: str
    name: str
    kind: str = "resource"
    owner: str = ""
    status: str = "available"
    meta: dict[str, Any] = Field(default_factory=dict)
    created_ts: str = ""


class WorkAllocation(BaseModel):
    id: str
    resource_id: str
    assignee: str
    purpose: str = ""
    status: str = "allocated"
    ts: str = ""


class RhizomeMembershipRecord(BaseModel):
    id: str
    ts: str
    member_id: str
    member_name: str
    role: str = "member"
    circles: list[str] = Field(default_factory=list)
    status: str = "active"  # active | former | guest
    recorded_by: str
    notes: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class WorkLogRecord(BaseModel):
    id: str
    ts: str
    member_id: str
    member_name: str
    description: str
    hours: float = 0.0
    kind: str = "labor"  # labor | care | governance | maintenance | research | coordination
    task_id: Optional[str] = None
    goal_id: Optional[str] = None
    contribution_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    logged_by: str
    meta: dict[str, Any] = Field(default_factory=dict)


class GovernanceRuleRecord(BaseModel):
    id: str
    ts: str
    title: str
    description: str
    kind: str = "policy"  # policy | access | economic | care | moderation
    scope: str = "tribe"  # rhizome | business | social | health | federated
    applies_to: list[str] = Field(default_factory=list)
    status: str = "active"  # draft | active | deprecated
    defined_by: str
    meta: dict[str, Any] = Field(default_factory=dict)


class EconomicIntentRecord(BaseModel):
    id: str
    ts: str
    title: str
    description: str = ""
    created_by: str
    kind: str = "need"  # need | offer | request | proposal
    target_members: list[str] = Field(default_factory=list)
    resource_ids: list[str] = Field(default_factory=list)
    status: str = "open"  # open | matched | withdrawn | completed
    notes: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class EconomicCommitmentRecord(BaseModel):
    id: str
    ts: str
    title: str
    description: str = ""
    committed_by: str
    owed_by: str
    owed_to: str = ""
    resource_ids: list[str] = Field(default_factory=list)
    task_id: Optional[str] = None
    due_ts: Optional[str] = None
    status: str = "open"  # open | fulfilled | released | cancelled
    notes: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class EconomicAgreementRecord(BaseModel):
    id: str
    ts: str
    title: str
    description: str = ""
    created_by: str
    parties: list[str] = Field(default_factory=list)
    commitment_ids: list[str] = Field(default_factory=list)
    status: str = "active"  # draft | active | closed
    notes: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class RhizomeEconomyProfileRecord(BaseModel):
    id: str
    ts: str
    created_by: str
    mission: str
    recognized_value_types: list[str] = Field(default_factory=list)
    distribution_logic: str
    governance_style: str
    pricing_modes: list[str] = Field(default_factory=list)
    solidarity_policy: str = ""
    external_alliances: list[str] = Field(default_factory=list)
    notes: str = ""
    status: str = "active"  # draft | active | deprecated
    meta: dict[str, Any] = Field(default_factory=dict)


class FederationAgreementRecord(BaseModel):
    id: str
    ts: str
    created_by: str
    title: str
    partner_rhizome: str = Field(alias="partner_tribe")  # legacy wire name
    partner_slug: Optional[str] = None
    agreement_type: str = "alliance"  # alliance | mutual_aid | commercial | research
    scopes: list[str] = Field(default_factory=list)
    description: str = ""
    status: str = "proposed"  # proposed | active | paused | closed
    resource_ids: list[str] = Field(default_factory=list)
    related_agreement_ids: list[str] = Field(default_factory=list)
    notes: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class EconomicAgentRecord(BaseModel):
    id: str
    ts: str
    name: str
    created_by: str
    role: str = "member"
    obligations: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    resource_ids: list[str] = Field(default_factory=list)
    contribution_ids: list[str] = Field(default_factory=list)
    status: str = "active"  # active | paused | offline | retired
    notes: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class ProtocolTermRecord(BaseModel):
    id: str
    ts: str
    term: str
    definition: str
    created_by: str
    domain: str = "economic"  # economic | governance | care | technical | research
    tags: list[str] = Field(default_factory=list)
    status: str = "active"  # active | draft | deprecated
    notes: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class CareRecord(BaseModel):
    id: str
    ts: str
    member_id: str
    member_name: str
    care_type: str = "check_in"  # check_in | support | mediation | rest | celebration
    domain: str = "social"  # physical | mental | social | economic
    summary: str
    beneficiaries: list[str] = Field(default_factory=list)
    hours: float = 0.0
    notes: str = ""
    recorded_by: str
    tags: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class RhythmRecord(BaseModel):
    id: str
    ts: str
    name: str
    cadence: str
    purpose: str
    participants: list[str] = Field(default_factory=list)
    care_required: bool = False
    created_by: str
    status: str = "active"  # active | paused | retired
    notes: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class ContributionRecord(BaseModel):
    id: str
    ts: str
    contributor_id: str
    contributor_name: str
    kind: str = "labor"  # labor | expense | device_use | care | maintenance | research
    title: str
    task_id: Optional[str] = None
    resource_id: Optional[str] = None
    device_id: Optional[str] = None
    output_memory_id: Optional[str] = None
    quantity: float = 1.0
    unit: str = "unit"
    cost_amount: Optional[float] = None
    notes: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class ValueFlowRecord(BaseModel):
    id: str
    ts: str
    flow_type: str = "profit_distribution"
    distribution_id: str
    amount: float
    recorded_by: str
    source: str = ""
    distribution: dict[str, float] = Field(default_factory=dict)
    contribution_ids: list[str] = Field(default_factory=list)
    resource_ids: list[str] = Field(default_factory=list)
    task_ids: list[str] = Field(default_factory=list)
    notes: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class PhysicalEvent(BaseModel):
    id: str
    ts: str
    event_type: str
    description: str
    reported_by: str
    member_ids: list[str] = Field(default_factory=list)
    device_ids: list[str] = Field(default_factory=list)
    location_label: Optional[str] = None
    gps: Optional[dict[str, float]] = None
    sensitivity: str = "shared"  # shared | limited | private
    consent_required: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)


class SensingEvent(BaseModel):
    id: str
    ts: str
    member_id: str
    member_name: str
    kind: str = "biological"  # physical | biological | psychic | cybernetic
    signal_type: str
    value: Any
    unit: str = ""
    source: str = "manual"
    sensitivity: str = "private"  # shared | limited | private
    consent_required: bool = True
    visibility: str = "private"
    scope: str = "private"
    meta: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    id: str
    ts: str
    author: str
    kind: str = "say"  # say | system | counsel
    text: str
    in_reply_to: Optional[str] = None
    meta: dict[str, Any] = Field(default_factory=dict)  # provenance: model, origin


class Vote(BaseModel):
    member: str
    position: Position
    reason: Optional[str] = None
    ts: str = ""


class Proposal(BaseModel):
    id: str
    title: str
    text: str
    rule: Rule
    quorum: int
    opened_by: str
    opened_ts: str
    status: ProposalStatus = ProposalStatus.OPEN
    version: int = 1
    outcome: Optional[Outcome] = None
    votes: dict[str, Vote] = Field(default_factory=dict)  # member_id -> Vote


class Decision(BaseModel):
    id: str
    ts: str
    proposal_id: str
    proposal_title: str
    rule: Rule
    outcome: Outcome
    tally: dict[str, int] = Field(default_factory=dict)
    quorum_required: int = 1
    votes_cast: int = 0
    closed_by: str = ""
    dissent: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""


class MemoryEntry(BaseModel):
    id: str
    ts: str
    kind: str = "note"  # note | charter | fact | event | summary | decision
    title: str
    text: str
    tags: list[str] = Field(default_factory=list)
    author: str = ""
    human: bool = True  # governance: human vs AI authorship stays visible
    visibility: str = "shared"  # shared | private | restricted
    source: str = ""  # provenance: self_report | imported | agent | decision | external
    audience: list[str] = Field(default_factory=lambda: ["rhizome"])
    revisions: list[str] = Field(default_factory=list)  # append-only: old text kept
    scope: str = "tribe"  # rhizome | research | federated
    meta: dict[str, Any] = Field(default_factory=dict)


class PrivateNote(BaseModel):
    id: str
    ts: str
    owner_id: str
    owner_name: str
    kind: str = "note"
    title: str
    text: str
    tags: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class EntityRef(BaseModel):
    kind: str
    id: str


class AssemblageComponent(BaseModel):
    """One identifiable part of a composite actor (assemblage).

    ``kind`` names the component type (member, device, resource,
    memory, lexicon, tool, network, language, external...); ``ref``
    points at it when it is a kernel entity, ``label`` when it is an
    external part (the Internet, a language, a corporation). Provenance
    stays: components are never dissolved into the assemblage.
    """

    kind: str
    ref: Optional[EntityRef] = None
    label: str = ""
    role: str = ""  # e.g. "human partner", "reasoning core", "sensor"
    meta: dict[str, Any] = Field(default_factory=dict)


class AssemblageRecord(BaseModel):
    """A composite actor: AI = human + LLM + language + the Internet.

    PCM's central claim is that an AI is never an isolated model but a
    sociotechnical assemblage. This record makes that claim part of the
    data model: an assemblage is a *member in its own right* (it can
    speak, propose, vote where permitted) while its components stay
    individually identifiable kernel entities or labelled externals.

    Composition is a governance/ontology statement, NOT a consciousness
    claim: constituting one actor does not assert one unified subject.
    """

    id: str
    ts: str
    name: str
    member_id: Optional[str] = None  # the member slot acting as this assemblage
    components: list[AssemblageComponent] = Field(default_factory=list)
    description: str = ""
    status: str = "active"  # active | dissolved
    created_by: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class EntityLink(BaseModel):
    id: str
    ts: str
    source: EntityRef
    target: EntityRef
    relation: str
    linked_by: str
    meta: dict[str, Any] = Field(default_factory=dict)


class Event(BaseModel):
    """One fact in the rhizome's history. The rhizome's memory IS this log."""

    id: str
    type: str
    ts: str
    actor: str
    payload: dict[str, Any] = Field(default_factory=dict)
