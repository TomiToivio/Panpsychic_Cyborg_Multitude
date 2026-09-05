# -*- coding: utf-8 -*-
"""Thin Hermes integration for Panpsychic Cyborg Multitude.

Hermes is a technological node inside the Multitude, not the Multitude
itself. This package keeps the dependency direction one-way:

Hermes -> adapter/tools -> kernel
"""
from multitude.integrations.hermes.adapter import (
    HermesPermissionError,
    HermesPermissions,
    MultitudeHermesAdapter,
)
from multitude.integrations.hermes.agent import HermesAgent, HermesAgentUnavailable

__all__ = [
    "HermesAgent",
    "HermesAgentUnavailable",
    "HermesPermissionError",
    "HermesPermissions",
    "MultitudeHermesAdapter",
]
