# -*- coding: utf-8 -*-
"""Panpsychic Cyborg Multitude - tribe kernel for hybrid human-AI groups.

A tribe is a small collective of biological nodes (humans) and
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
    TribeEconomyProfileRecord,
    TribeMembershipRecord,
    Vote,
    WorkLogRecord,
)
from multitude.service import MultitudeService
from multitude.store import TribeStore
from multitude.tribe import Tribe, TribeError

__all__ = [
    "Tribe",
    "TribeStore",
    "MultitudeService",
    "NoosphereGraphBridge",
    "TribeError",
    "Event",
    "Member",
    "LexiconEntry",
    "DeviceRecord",
    "BiometricSignalRecord",
    "PhysicalEvent",
    "TribeMembershipRecord",
    "WorkLogRecord",
    "GovernanceRuleRecord",
    "EconomicIntentRecord",
    "EconomicCommitmentRecord",
    "EconomicAgreementRecord",
    "TribeEconomyProfileRecord",
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
