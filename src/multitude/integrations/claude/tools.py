"""Small audited tool surface for Claude Code.

No unrestricted shell or raw kernel object is exposed here. Every mutating
operation delegates to the adapter, which applies the same permission checks
and canonical service calls as Hermes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .adapter import ClaudeCodeAdapter


@dataclass
class ClaudeTools:
    adapter: ClaudeCodeAdapter

    def status(self):
        return self.adapter.get_status()

    def own_identity(self):
        return self.adapter.get_agent()

    def recent_events(self, limit: int = 20, days: Optional[int] = None):
        return self.adapter.get_recent_events(limit=limit, days=days)

    def search_memory(self, query: str):
        return self.adapter.search_memory(query)

    def proposals(self, status: Optional[str] = None):
        return self.adapter.list_proposals(status=status)

    def goals(self, status: Optional[str] = None):
        return self.adapter.list_goals(status=status)

    def propose(self, title: str, text: str):
        return self.adapter.create_proposal(title, text)

    def vote(self, proposal_id: str, position: str, reason: str = ""):
        return self.adapter.cast_vote(proposal_id, position, reason=reason)

    def governance_change(self):
        return self.adapter.modify_governance()
