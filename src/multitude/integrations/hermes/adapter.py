# -*- coding: utf-8 -*-
"""Thin service boundary between Hermes and the Multitude kernel."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from multitude import goals
from multitude.integrations.hermes.config import DEFAULT_LANGUAGES
from multitude.models import AgentProfile, NodeKind, Position
from multitude.service import MultitudeService
from multitude.tribe import Tribe


class HermesPermissionError(PermissionError):
    """Hermes can technically do something but is not authorized to do it."""


@dataclass
class HermesPermissions:
    read_memory: bool = True
    search_memory: bool = True
    summarize: bool = True
    analyze: bool = True
    counsel: bool = True
    draft: bool = True
    propose: bool = True
    vote: bool = False
    block: bool = False
    spend_money: bool = False
    transfer_assets: bool = False
    add_members: bool = False
    remove_members: bool = False
    modify_governance: bool = False
    delete_history: bool = False

    def require(self, action: str) -> None:
        if not getattr(self, action, False):
            raise HermesPermissionError(f"Hermes agent is not authorized to {action}")

    def as_dict(self) -> dict[str, bool]:
        return dict(self.__dict__)


@dataclass
class MultitudeHermesAdapter:
    """Narrow, kernel-facing API for Hermes-like agents."""

    tribe: Tribe
    agent_name: str = "Panpsychic Cyborg Multitude"
    role: str = "knowledge_steward"
    model: Optional[str] = None
    permissions: HermesPermissions = field(default_factory=HermesPermissions)

    @property
    def service(self) -> MultitudeService:
        return MultitudeService(self.tribe)

    def ensure_agent(self) -> Any:
        member = self.tribe.member_by_name(self.agent_name)
        if member is None:
            member = self.tribe.join(
                self.agent_name,
                NodeKind.TECHNOLOGICAL,
                model=self.model,
                voting=False,  # authority via permissions, not vote flag
                profile=self._default_profile(),
            )
        elif member.kind != NodeKind.TECHNOLOGICAL:
            raise HermesPermissionError(
                f"member '{self.agent_name}' exists but is not technological"
            )
        self._ensure_identity_layers(member.name)
        roles = list(member.meta.get("roles", []))
        if self.role not in roles:
            roles.append(self.role)
        desired_vote = member.voting if self.permissions.vote else False
        updated = self.tribe.update_member(
            member.name,
            model=self.model,
            voting=desired_vote,
            meta={
                "roles": roles,
                "runtime": "hermes-agent",
                "permissions": self.permissions.as_dict(),
            },
        )
        return updated

    def _default_profile(self) -> AgentProfile:
        return AgentProfile(
            physical={
                "location_label": "local-machine",
                "notes": "host=local-machine; location=unspecified",
            },
            biological={
                "is_biological": False,
                "species": "not_applicable",
                "notes": "organism=not_applicable",
            },
            social={
                "tribe_role": self.role,
                "notes": "technological node in the tribe",
            },
            linguistic={
                "languages": list(DEFAULT_LANGUAGES),
                "notes": "runtime=hermes-agent; model=configurable",
            },
            psychic={
                "is_conscious": None,
                "state": "unknown",
                "notes": "consciousness_status=unknown; self_reported_state=not_applicable",
            },
            cybernetic={
                "interface_mode": "text",
                "network_links": ["multitude-kernel"],
                "devices": ["terminal", "filesystem", "llm"],
                "model_runtime": self.model or "configurable",
                "notes": "interfaces=terminal,filesystem,llm,multitude-kernel",
            },
        )

    def _ensure_identity_layers(self, member_name: str) -> None:
        member = self.tribe._require_member(member_name)
        wants = {
            "physical": {
                "location_label": member.profile.physical.location_label or "local-machine",
                "notes": member.profile.physical.notes or "host=local-machine; location=unspecified",
            },
            "biological": {
                "is_biological": False,
                "species": member.profile.biological.species or "not_applicable",
                "notes": member.profile.biological.notes or "organism=not_applicable",
            },
            "social": {
                "tribe_role": member.profile.social.tribe_role or self.role,
                "notes": member.profile.social.notes or "technological node in the tribe",
            },
            "linguistic": {
                "languages": member.profile.linguistic.languages or list(DEFAULT_LANGUAGES),
                "notes": member.profile.linguistic.notes or "runtime=hermes-agent; model=configurable",
            },
            "psychic": {
                "is_conscious": member.profile.psychic.is_conscious,
                "state": member.profile.psychic.state or "unknown",
                "notes": member.profile.psychic.notes or "consciousness_status=unknown; self_reported_state=not_applicable",
            },
            "cybernetic": {
                "interface_mode": member.profile.cybernetic.interface_mode or "text",
                "network_links": member.profile.cybernetic.network_links or ["multitude-kernel"],
                "devices": member.profile.cybernetic.devices or ["terminal", "filesystem", "llm"],
                "model_runtime": member.profile.cybernetic.model_runtime or self.model or "configurable",
                "notes": member.profile.cybernetic.notes or "interfaces=terminal,filesystem,llm,multitude-kernel",
            },
        }
        for layer, changes in wants.items():
            if layer not in member.layers:
                self.tribe.record_layer(member.name, layer, changes, reported_by=member.name)

    def get_status(self) -> dict[str, Any]:
        self.permissions.require("read_memory")
        return self.service.status()

    def get_agent(self, name: Optional[str] = None) -> Any:
        self.permissions.require("read_memory")
        self.ensure_agent()
        member = self.tribe._require_member(name or self.agent_name)
        return member

    def list_agents(self) -> list[Any]:
        self.permissions.require("read_memory")
        return [self.tribe._require_member(item["name"]) for item in self.service.list_agents()]

    def get_recent_events(self, limit: int = 20, days: Optional[int] = None) -> list[Any]:
        self.permissions.require("read_memory")
        events = self.tribe.store.replay()
        if days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            filtered = []
            for ev in events:
                try:
                    when = datetime.fromisoformat(ev.ts)
                except ValueError:
                    when = None
                if when is None or when >= cutoff:
                    filtered.append(ev)
            events = filtered
        return events[-limit:]

    def search_memory(self, query: str) -> list[Any]:
        self.permissions.require("search_memory")
        return self.tribe.search_memory(query)

    def list_proposals(self, status: Optional[str] = None) -> list[Any]:
        self.permissions.require("read_memory")
        items = self.service.list_proposals(status=status)
        return [self.tribe.proposals[item["id"]] for item in items]

    def list_goals(self, status: Optional[str] = None) -> list[Any]:
        self.permissions.require("read_memory")
        items = list(self.tribe.goals.values())
        if status is not None:
            items = [g for g in items if g.status == status]
        return sorted(items, key=lambda g: g.opened_ts)

    def create_proposal(self, title: str, text: str, author_name: Optional[str] = None) -> Any:
        self.permissions.require("propose")
        self.ensure_agent()
        data = self.service.create_proposal(author=author_name or self.agent_name, title=title, text=text)
        return self.tribe.proposals[data["id"]]

    def cast_vote(
        self,
        proposal_id: str,
        position: Position | str,
        voter_name: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Any:
        pos = Position(position) if isinstance(position, str) else position
        self.permissions.require("vote")
        if pos == Position.BLOCK:
            self.permissions.require("block")
        self.ensure_agent()
        data = self.service.vote(proposal_id, voter_name or self.agent_name, pos, reason=reason)
        return self.tribe.proposals[proposal_id].votes[data["vote"]["member"]]

    def close_proposal(self, proposal_id: str, closer_name: Optional[str] = None) -> Any:
        self.permissions.require("modify_governance")
        self.ensure_agent()
        return self.tribe.close_proposal(proposal_id, closer_name or self.agent_name)

    def modify_governance(self, *_args: Any, **_kwargs: Any) -> None:
        self.permissions.require("modify_governance")
        raise HermesPermissionError("governance mutation is not implemented through Hermes")

    def current_goals_summary(self) -> dict[str, Any]:
        self.permissions.require("read_memory")
        goals_by_category: dict[str, list[str]] = {"business": [], "social": [], "health": []}
        for goal in self.tribe.goals.values():
            if goal.status == goals.GoalStatus.OPEN.value:
                goals_by_category.setdefault(goal.category, []).append(goal.title)
        return goals_by_category
