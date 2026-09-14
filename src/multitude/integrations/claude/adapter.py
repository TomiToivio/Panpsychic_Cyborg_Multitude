# -*- coding: utf-8 -*-
"""Claude Code as a thin PCM technological participant.

The implementation deliberately reuses MultitudeHermesAdapter so Claude and
Hermes share the same canonical service calls and permission checks. Claude
Code itself is not imported or required by this package.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from multitude.integrations.hermes.adapter import (
    HermesPermissionError,
    HermesPermissions,
    MultitudeHermesAdapter,
)
from multitude.models import AgentProfile

ClaudePermissions = HermesPermissions
ClaudePermissionError = HermesPermissionError


@dataclass
class ClaudeCodeAdapter(MultitudeHermesAdapter):
    """Low-privilege Claude Code participant using PCM's canonical boundary."""

    agent_name: str = "agent:claude-code"
    role: str = "developer_research_assistant"
    model: Optional[str] = None

    def _default_profile(self) -> AgentProfile:
        return AgentProfile(
            physical={
                "location_label": "external-runtime",
                "notes": "host=external-runtime; location=unspecified",
            },
            biological={
                "is_biological": False,
                "species": "not_applicable",
                "notes": "organism=not_applicable",
            },
            social={
                "tribe_role": self.role,
                "notes": "technological participant; proposals are not collective decisions",
            },
            linguistic={
                "languages": ["en"],
                "notes": "runtime=claude-code; external agent caller",
            },
            psychic={
                "is_conscious": None,
                "state": "unknown",
                "notes": "consciousness status is epistemically open and grants no authority",
            },
            cybernetic={
                "interface_mode": "text",
                "network_links": ["multitude-kernel"],
                "devices": ["external-agent-runtime"],
                "model_runtime": self.model or "externally-managed",
                "notes": "Claude Code reaches PCM only through the adapter/service boundary",
            },
        )

    def ensure_agent(self) -> Any:
        member = super().ensure_agent()
        # The inherited path performs all canonical identity checks and policy
        # enforcement. Correct only runtime-specific metadata afterwards.
        roles = list(member.meta.get("roles", []))
        if self.role not in roles:
            roles.append(self.role)
        return self.rhizome.update_member(
            member.name,
            model=self.model,
            voting=(member.voting if self.permissions.vote else False),
            meta={
                "roles": roles,
                "runtime": "claude-code",
                "permissions": self.permissions.as_dict(),
                "actor_id": self.agent_name,
            },
        )

    def audit_context(self, *, action: str, correlation_id: str | None = None) -> dict[str, Any]:
        """Provenance context for an explicit caller-controlled event write."""
        return {
            "actor_id": self.agent_name,
            "runtime": "claude-code",
            "action": action,
            "correlation_id": correlation_id or "",
            "permissions": self.permissions.as_dict(),
            "consciousness_authority": False,
        }
