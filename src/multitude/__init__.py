# -*- coding: utf-8 -*-
"""Panpsychic Cyborg Multitude - rhizome kernel for hybrid human-AI groups.

A rhizome is a small collective of biological nodes (humans) and
technological nodes (LLM-backed agents) with a shared stream, shared
memory, and shared decision-making. All state is derived by replaying
an append-only event log.
"""
__version__ = "0.1.0"

from multitude.models import (
    BiometricSignalRecord,
    CareRecord,
    Decision,
    EconomicAgentRecord,
    EconomicAgreementRecord,
    EconomicCommitmentRecord,
    EconomicIntentRecord,
    Event,
    FederationAgreementRecord,
    GovernanceRuleRecord,
    Layer,
    LexiconEntry,
    Member,
    MemoryEntry,
    PrivateNote,
    Message,
    NodeKind,
    Outcome,
    DeviceRecord,
    PhysicalEvent,
    Position,
    Proposal,
    ProposalStatus,
    ProtocolTermRecord,
    RhythmRecord,
    Rule,
    RhizomeEconomyProfileRecord,
    RhizomeMembershipRecord,
    Vote,
    WorkLogRecord,
)
from multitude.service import MultitudeService
from multitude.store import RhizomeStore
from multitude.rhizome import Rhizome, RhizomeError

__all__ = [
    "Rhizome",
    "RhizomeStore",
    "MultitudeService",
    "NoosphereGraphBridge",
    "RhizomeError",
    "Event",
    "Member",
    "LexiconEntry",
    "DeviceRecord",
    "BiometricSignalRecord",
    "PhysicalEvent",
    "RhizomeMembershipRecord",
    "WorkLogRecord",
    "GovernanceRuleRecord",
    "EconomicIntentRecord",
    "EconomicCommitmentRecord",
    "EconomicAgreementRecord",
    "RhizomeEconomyProfileRecord",
    "FederationAgreementRecord",
    "CareRecord",
    "RhythmRecord",
    "Message",
    "Proposal",
    "Vote",
    "Decision",
    "MemoryEntry",
    "PrivateNote",
    "NodeKind",
    "Position",
    "Rule",
    "Outcome",
    "ProposalStatus",
    "Layer",
    "__version__",
]
